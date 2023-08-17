import json
import os
import shutil
import struct
import zipfile
from datetime import datetime
from distutils.dir_util import remove_tree
from typing import Dict, List

from vpt_core import log
from vpt_core.io.vzgfs import Protocol, filesystem_for_protocol, protocol_path_split, vzg_open, retrying_attempts

from vpt.update_vzg.imageparams import ImageParams
from vpt.update_vzg.manifestgen import ManifestGenerator
from vpt.utils.general_data import load_images_manifest, write_json_file


def create_manifest(datasetName: str, datasetPath: str, zPlanes: int, imageParams: ImageParams):
    manifest = ManifestGenerator(imageParams.textureSize, imageParams.micronToPixelMatrix, datasetName)

    manifest.set_planes_count(zPlanes)
    manifest.set_cells_status(True)
    manifest.set_transcripts_status(True)

    pyrMosaicDict = load_images_manifest(datasetPath)["mosaic_pyramid_files"]

    imageDict = parse_picture_manifest(pyrMosaicDict)
    manifest.set_image_dict(imageDict)
    manifest_data = manifest.create_json_manifest()

    write_json_file(manifest_data, f"{datasetPath}", "manifest.json")


def parse_picture_manifest(pictureManifestJson) -> dict:
    picture_manifest_dict: Dict = {}

    for mosaic in pictureManifestJson:
        tagName = mosaic["stain"]
        if tagName not in picture_manifest_dict:
            picture_manifest_dict[tagName] = {"Files": []}

        z = int(mosaic["z"])
        picture_manifest_dict[tagName]["Files"].append({"zPlane": z, "Name": mosaic["file_name"]})

    return picture_manifest_dict


class VzgRepacker:
    features_folder: str = "features"
    geometry_packed_folder: str = "cells_packed"
    assemble_folder: str = "assemble"

    def __init__(self, originVzgPath: str, userBuildFolderPath):
        self._originVzgPath: str = originVzgPath
        self._datasetName: str = os.path.basename(self._originVzgPath)[:-4]

        temp_subfolder = f"vzg_{datetime.now().strftime('%Y-%m-%dT%H_%M_%S_%f')}"
        self._user_folder_path = userBuildFolderPath
        self._tempBuildFolderPath = os.path.join(userBuildFolderPath, temp_subfolder)
        self._tempVzgFolderPath = os.path.join(self._tempBuildFolderPath, self._datasetName)

        self._z_planes_count = -1
        self._logs: List[str] = []

    def get_dataset_folder(self):
        return self._tempVzgFolderPath

    def get_build_temp_folder(self):
        return self._tempBuildFolderPath

    def get_feature_folder(self, feature_name):
        return os.path.join(self._tempVzgFolderPath, self.features_folder, feature_name)

    def read_dataset_z_planes_count(self) -> int:
        if self._z_planes_count > 0:
            return self._z_planes_count

        imageManifestPath = os.path.join(self._tempVzgFolderPath, "pictures", "manifest.json")
        with open(imageManifestPath, "r") as f:
            imageManifest = json.load(f)

        zPlanesNumbers = []
        for tiffDescription in imageManifest["mosaic_files"]:
            zPlanesNumbers.append(tiffDescription["z"])

        self._z_planes_count = max(zPlanesNumbers) + 1
        return self._z_planes_count

    def unpack_vzg(self):
        protocol, path_inside_fs = protocol_path_split(self._originVzgPath)
        if protocol != Protocol.LOCAL:  # Protocol.S3 or Protocol.GCS
            fs = filesystem_for_protocol(protocol)
            vzgInputPath = os.path.join(self._tempBuildFolderPath, f"{self._datasetName}.vzg")
            fs.get(self._originVzgPath, vzgInputPath)
        else:  # Protocol.LOCAL
            vzgInputPath = self._originVzgPath

        for attempt in retrying_attempts():
            with attempt, vzg_open(vzgInputPath, "rb") as f:
                with zipfile.ZipFile(f) as zip_ref:
                    zip_ref.extractall(self._tempVzgFolderPath)
        self.convert_vzg_to_v2()

        log.info(f"{self._originVzgPath} unpacked!")

    def convert_vzg_to_v2(self):
        old_cells_folder = os.path.join(self._tempVzgFolderPath, self.geometry_packed_folder)
        old_assemble_folder = os.path.join(self._tempVzgFolderPath, self.assemble_folder)

        if os.path.exists(os.path.join(self._tempVzgFolderPath, self.features_folder)) and (
            os.path.exists(old_cells_folder) or os.path.exists(old_assemble_folder)
        ):
            raise ValueError("Incorrect vzg structure")

        cell_feature_path = self.get_feature_folder("cell")
        if os.path.exists(old_cells_folder):
            shutil.copytree(old_cells_folder, os.path.join(cell_feature_path, self.geometry_packed_folder))
            shutil.rmtree(old_cells_folder)
        if os.path.exists(old_assemble_folder):
            shutil.copytree(old_assemble_folder, os.path.join(cell_feature_path, self.assemble_folder))
            shutil.rmtree(old_assemble_folder)

        manifest_path = os.path.join(self._tempVzgFolderPath, "manifest.json")
        with open(manifest_path, "r") as f:
            manifest_data = json.load(f)
            manifest_data["Version"] = "2.0.0"

        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=4)

    def check_update_manifest_genes_info_array(self, imageParams: ImageParams):
        maxZPlane = self.read_dataset_z_planes_count()
        vzgRootFolder = os.listdir(self._tempVzgFolderPath)

        if "manifest.json" not in vzgRootFolder:
            create_manifest(self._datasetName, self._tempVzgFolderPath, maxZPlane, imageParams)
            log.info("New manifest created")
        else:
            self._add_cells_flag_to_manifest()

        if "genes_info_array.json" not in os.listdir(os.path.join(self._tempVzgFolderPath, "genes")):
            self.generate_genes_info_array()

    def repack_vzg_file(self, outputVzgFilePath: str):
        self._add_info_to_manifest()
        if os.path.exists(f"{outputVzgFilePath}.vzg"):
            os.remove(f"{outputVzgFilePath}.vzg")

        protocol, path_inside_fs = protocol_path_split(outputVzgFilePath)
        if protocol != Protocol.LOCAL:  # Protocol.S3 or Protocol.GCS
            tempNewVzgPath = os.path.join(self._tempBuildFolderPath, os.path.basename(outputVzgFilePath))
            shutil.make_archive(tempNewVzgPath, "zip", self._tempVzgFolderPath)
            os.rename(f"{tempNewVzgPath}.zip", f"{tempNewVzgPath}.vzg")

            fs = filesystem_for_protocol(protocol)
            fs.put(f"{tempNewVzgPath}.vzg", f"{path_inside_fs}.vzg")
        else:
            shutil.make_archive(outputVzgFilePath, "zip", self._tempVzgFolderPath)
            os.rename(f"{outputVzgFilePath}.zip", f"{outputVzgFilePath}.vzg")
        log.info("new vzg file created")

        if os.path.exists(self._tempBuildFolderPath):
            remove_tree(self._tempBuildFolderPath)

        if not os.listdir(self._user_folder_path):
            remove_tree(self._user_folder_path)
        log.info("temp files deleted")

    def _add_cells_flag_to_manifest(self):
        manifestPath = os.path.join(self._tempVzgFolderPath, "manifest.json")
        with open(manifestPath, "r") as f:
            manifestData = json.load(f)
            manifestData["Cells"] = True

        with open(manifestPath, "w") as f:
            json.dump(manifestData, f, indent=4)

    def _add_info_to_manifest(self):
        manifest_path = os.path.join(self._tempVzgFolderPath, "manifest.json")
        update_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        with open(manifest_path, "r") as f:
            manifest_data = json.load(f)

        if manifest_data.get("Info") is None:
            manifest_data["Info"] = []
        for info in self._logs:
            manifest_data["Info"].append(info)
        manifest_data["Updated"] = update_time

        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=4)

    def log_manifest(self, info: str):
        update_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self._logs.append(" ".join([update_time, "Updated by VPT", info]))

    def get_manifest_channels(self):
        manifest_path = os.path.join(self._tempVzgFolderPath, "manifest.json")
        with open(manifest_path, "r") as f:
            manifest_data = json.load(f)
        return list(manifest_data["Images"].keys())

    def read_genes_info_array(self) -> dict:
        gene_info_path = os.path.join(self._tempVzgFolderPath, "genes", "genes_info_array.json")

        with open(gene_info_path, "r") as f:
            gene_info_data = json.load(f)

        return gene_info_data

    def update_genes_info_array(self, gene_data: Dict, sequential_genes: List[str]):
        info_path = os.path.join(self._tempVzgFolderPath, "genes")
        source_path = os.path.join(info_path, "source_genes_info_array.json")
        new_path = os.path.join(info_path, "genes_info_array.json")

        with open(source_path, "w") as f:
            json.dump(gene_data, f, indent=4)
        gene_data["transcriptsPerGeneList"] = list(
            filter(lambda gene: gene["name"] not in sequential_genes, gene_data["transcriptsPerGeneList"])
        )
        with open(new_path, "w") as f:
            json.dump(gene_data, f, indent=4)

        self.log_manifest(f"{len(sequential_genes)} sequential genes excluded from VZG file")

    def generate_genes_info_array(self):
        with open(os.path.join(self._tempVzgFolderPath, "genes", "gene_name_array.bin"), "rb") as f:
            gene_name_array_bytes = f.read()

        genes_names_list = self._unpack_gene_name_array(gene_name_array_bytes)
        genes_count_list = self._unpack_genes_count()

        infoList = []
        transcriptsCount = 0
        for i, name in enumerate(genes_names_list):
            infoList.append({"name": name, "count": genes_count_list[i]})
            transcriptsCount += genes_count_list[i]

        genes_info_array = {"transcriptsCount": transcriptsCount, "transcriptsPerGeneList": infoList}
        gene_info_path = os.path.join(self._tempVzgFolderPath, "genes", "genes_info_array.json")
        with open(gene_info_path, "w") as f:
            json.dump(genes_info_array, f, indent=4)

        print("Genes info array created")

    @staticmethod
    def _unpack_gene_name_array(gene_name_array: bytes) -> list:
        genes_count = struct.unpack("<I", gene_name_array[0:4])[0]
        bytes_per_gene = struct.unpack("<I", gene_name_array[4:8])[0]
        if bytes_per_gene != 16:
            raise TypeError

        genes_list = []
        for gene_idx in range(genes_count):
            genes_list.append(gene_name_array[8 + gene_idx * 16 : 24 + gene_idx * 16].decode("utf-8").rstrip("\x00"))

        return genes_list

    @staticmethod
    def _unpack_group(arr, start_byte):
        start_index = struct.unpack("<I", arr[start_byte : start_byte + 4])[0]
        first = struct.unpack("<I", arr[start_byte + 4 : start_byte + 8])[0]
        second = struct.unpack("<I", arr[start_byte + 8 : start_byte + 12])[0]

        count = start_index >> 27

        gene_idx = ((first & 0x000000FF) << 8) + (second & 0x000000FF)

        return count, gene_idx

    def _unpack_genes_count(self) -> Dict[int, int]:
        genes_count_dict: Dict[int, int] = {}
        for z_idx in range(self._z_planes_count):
            genes_path = os.path.join(self._tempVzgFolderPath, "genes", f"genes_{z_idx}.bin")
            with open(genes_path, "rb") as f:
                genes_btr = f.read()
            groups_count = struct.unpack("<I", genes_btr[4:8])[0]

            start_byte = 8
            for i in range(groups_count):
                count, gene_idx = VzgRepacker._unpack_group(genes_btr, start_byte)
                start_byte += 60
                if gene_idx in genes_count_dict:
                    genes_count_dict[gene_idx] += count
                else:
                    genes_count_dict[gene_idx] = count

        return genes_count_dict
