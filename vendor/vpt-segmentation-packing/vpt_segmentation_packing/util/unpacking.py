import math
import struct
from typing import List, Tuple

import numpy as np

BYTES_PER_POLYGON = (136, 36, 4)


def unpack4_points(basePoint, packedBytes):
    offsets = np.zeros(4, dtype=np.uint32)
    offsets[0] = np.uint32(packedBytes[0] >> 8)
    offsets[1] = ((np.uint32(packedBytes[0] << 24)) >> 8) + np.uint32(packedBytes[1] >> 16)
    offsets[2] = np.uint32(np.uint32(packedBytes[1] << 16) >> 8) + np.uint32(packedBytes[2] >> 24)
    offsets[3] = np.uint32(np.uint32(packedBytes[2] << 8) >> 8)

    unpackPoints = np.zeros((4, 2), dtype=np.float32)
    for i in range(4):
        unpackPoints[i][0] = basePoint[0] + (offsets[i] >> 12)
        unpackPoints[i][1] = basePoint[1] + (offsets[i] & ((1 << 12) - 1))

    return unpackPoints


def unpack2_points(basePoint, packedBytes):
    offsets = np.zeros(2, dtype=np.uint32)
    offsets[0] = np.uint32(packedBytes[0] >> 16)
    offsets[1] = np.uint32((np.uint32(packedBytes[0] << 16)) >> 16)

    unpackPoints = np.zeros((2, 2), dtype=np.float32)
    for i in range(2):
        unpackPoints[i][0] = basePoint[0] + (offsets[i] >> 8) * 4
        unpackPoints[i][1] = basePoint[1] + (offsets[i] & ((1 << 8) - 1)) * 4

    return unpackPoints


def unpack8_points(basePoint, packedBytes):
    offsets = np.zeros(8, dtype=np.uint32)
    offsets[0] = np.uint32(packedBytes[0] >> 20)
    offsets[1] = np.uint32(np.uint32(packedBytes[0] << 12) >> 20)
    offsets[2] = np.uint32(np.uint32(np.uint32(packedBytes[0] << 24) >> 20) + np.uint32(packedBytes[1] >> 28))
    offsets[3] = np.uint32(np.uint32(packedBytes[1] << 4) >> 20)

    offsets[4] = np.uint32(np.uint32(packedBytes[1] << 16) >> 20)
    offsets[5] = np.uint32(np.uint32((np.uint32(packedBytes[1] << 28)) >> 20) + np.uint32(packedBytes[2] >> 24))

    offsets[6] = np.uint32(np.uint32(packedBytes[2] << 8) >> 20)
    offsets[7] = np.uint32(np.uint32(packedBytes[2] << 20) >> 20)

    unpackPoints = np.zeros((8, 2), dtype=np.float32)
    for i in range(8):
        unpackPoints[i][0] = basePoint[0] + (offsets[i] >> 6) * 16
        unpackPoints[i][1] = basePoint[1] + (offsets[i] & ((1 << 6) - 1)) * 16

    return unpackPoints


def create_octagon_pattern():
    positions = []
    vertsCount = 8
    for i in range(vertsCount):
        angle = (i / vertsCount) * math.pi * 2
        positions.append((math.cos(angle), math.sin(angle)))

    return positions


octagonPattern = create_octagon_pattern()


def unpack_lod0(pointsBtr, basePoint):
    originalPoints = []
    for polyIdx in range(11):
        byteIdx = 4 + polyIdx * 12
        first = np.uint32(struct.unpack("<I", pointsBtr[byteIdx : byteIdx + 4])[0])
        second = np.uint32(struct.unpack("<I", pointsBtr[byteIdx + 4 : byteIdx + 8])[0])
        third = np.uint32(struct.unpack("<I", pointsBtr[byteIdx + 8 : byteIdx + 12])[0])

        unpackedPoints = unpack4_points(basePoint, (first, second, third))
        originalPoints += list(unpackedPoints)

    return originalPoints


def unpack_lod1(pointsBtr, firstP):
    originalPoints = []
    for polyIdx in range(8):
        byteIdx = 4 + polyIdx * 4
        first = np.uint32(struct.unpack("<I", pointsBtr[byteIdx : byteIdx + 4])[0])
        unpackedPoints = unpack2_points(firstP, (first,))
        originalPoints += list(unpackedPoints)

    return originalPoints


def unpack_lod2(pointsBtr, firstP, transformationMatrix):
    originalPoints = []
    octagonWord = np.uint32(struct.unpack("<I", pointsBtr[0:4])[0]) & ((1 << 8) - 1)
    radius = np.uint32(octagonWord >> 4) + 1
    scale = (3.0 + np.uint32((octagonWord >> 2) & 3)) / 6.0
    alpha = math.pi * 0.25 * np.uint32(octagonWord & 3)

    for i in range(8):
        delta = (
            octagonPattern[i][0] * radius * transformationMatrix[0][0],
            octagonPattern[i][1] * radius * scale * transformationMatrix[1][1],
        )
        offsetX = delta[0] * math.cos(alpha) + delta[1] * math.sin(alpha)
        offsetY = -delta[0] * math.sin(alpha) + delta[1] * math.cos(alpha)
        originalPoints.append(np.asarray((firstP[0] + offsetX, firstP[1] + offsetY), dtype=np.int32))

    return originalPoints


def unpack_lod(lodLevelValue):
    return [unpack_lod0, unpack_lod1, unpack_lod2][lodLevelValue]


def unpack_polygon(lodLevelValue: int, polyData: bytes, imageSize, gridSize, transformationMatrix):
    basePoint = np.zeros(2, dtype=np.uint32)
    if lodLevelValue < 2:
        basePoint[1] = np.uint16(struct.unpack("<H", polyData[0:2])[0])
        basePoint[0] = np.uint16(struct.unpack("<H", polyData[2:4])[0])
        points = [unpack_lod0, unpack_lod1][lodLevelValue](polyData, basePoint)
    else:  # lodLevel == 2
        octagonWord = np.uint32(struct.unpack("<I", polyData[0:4])[0])
        basePoint[0] = np.uint32(octagonWord >> 20) / (1 << 12) / gridSize[0] * imageSize[0]
        basePoint[1] = np.uint32(np.uint32(octagonWord << 12) >> 20) / (1 << 12) / gridSize[0] * imageSize[0]
        points = unpack_lod2(polyData, basePoint, transformationMatrix)

    return points


def unpack_lods(
    tileData: bytes,
    lodLevelValue: int,
    imageSize: Tuple[int, int],
    gridSizeList: List[int],
    transformMatrix: np.ndarray,
    cornerPoint: Tuple,
) -> Tuple[List, np.ndarray]:
    outputList = []
    headerSize = 3
    count = np.uint32(struct.unpack("<I", tileData[8:12])[0])
    bytesPerPolygon = BYTES_PER_POLYGON[lodLevelValue]
    for i in range(count):
        polyData = tileData[12 + bytesPerPolygon * i : 12 + bytesPerPolygon * (i + 1)]
        points = unpack_polygon(lodLevelValue, polyData, imageSize, gridSizeList[lodLevelValue], transformMatrix)
        for p in points:
            p[0] += cornerPoint[0]
            p[1] += cornerPoint[1]
        # for

        outputList.append(points)

    startCellMap = headerSize * 4 + count * bytesPerPolygon
    cellMap = np.frombuffer(tileData[startCellMap : startCellMap + count * 4], dtype=np.uint32)
    return outputList, cellMap
