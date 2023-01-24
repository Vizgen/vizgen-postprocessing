import json
import os
import shutil
import zipfile
from distutils.dir_util import remove_tree

from vpt.filesystem import vzg_open
from vpt.filesystem.vzgfs import protocol_path_split, Protocol, filesystem_for_protocol
from vpt.update_vzg.imageparams import ImageParams
from vpt.update_vzg.manifestgen import ManifestGenerator
from vpt.utils.general_data import load_images_manifest, write_json_file


def create_manifest(datasetName: str,
                    datasetPath: str,
                    zPlanes: int,
                    imageParams: ImageParams
                    ):
    manifest = ManifestGenerator(
        imageParams.textureSize, imageParams.micronToPixelMatrix, datasetName)

    manifest.set_planes_count(zPlanes)
    manifest.set_cells_status(True)
    manifest.set_transcripts_status(True)

    pyrMosaicDict = load_images_manifest(datasetPath)['mosaic_pyramid_files']

    imageDict = parse_picture_manifest(pyrMosaicDict)
    manifest.set_image_dict(imageDict)
    manifest_data = manifest.create_json_manifest()

    write_json_file(manifest_data, f'{datasetPath}', 'manifest.json')


def parse_picture_manifest(pictureManifestJson) -> dict:
    pictureManifestDict = {}

    for mosaic in pictureManifestJson:
        tagName = mosaic['stain']
        if tagName not in pictureManifestDict:
            pictureManifestDict[tagName] = {'Files': []}

        zPlane = int(mosaic['z'])
        pictureManifestDict[tagName]['Files'].append({"zPlane": zPlane, "Name": mosaic['file_name']})

    return pictureManifestDict


class VzgRepacker:
    def __init__(self, originVzgPath: str, tempBuildFolderPath):
        self._originVzgPath: str = originVzgPath
        self._datasetName: str = os.path.basename(self._originVzgPath)[:-4]
        self._tempBuildFolderPath = tempBuildFolderPath
        self._tempVzgFolderPath = os.path.join(tempBuildFolderPath, self._datasetName)

        self._z_planes_count = -1

    def get_dataset_folder(self):
        return self._tempVzgFolderPath

    def read_dataset_z_planes_count(self) -> int:
        if self._z_planes_count > 0:
            return self._z_planes_count

        imageManifestPath = os.path.join(self._tempVzgFolderPath, 'pictures', 'manifest.json')
        with open(imageManifestPath, 'r') as f:
            imageManifest = json.load(f)

        zPlanesNumbers = []
        for tiffDescription in imageManifest['mosaic_files']:
            zPlanesNumbers.append(tiffDescription['z'])

        self._z_planes_count = max(zPlanesNumbers) + 1
        return self._z_planes_count

    def unpack_vzg(self):
        protocol, path_inside_fs = protocol_path_split(self._originVzgPath)
        if protocol != Protocol.LOCAL:  # Protocol.S3 or Protocol.GCS
            fs = filesystem_for_protocol(protocol)
            vzgInputPath = os.path.join(self._tempBuildFolderPath, f'{self._datasetName}.vzg')
            fs.get(self._originVzgPath, vzgInputPath)
        else:  # Protocol.LOCAL
            vzgInputPath = self._originVzgPath

        with vzg_open(vzgInputPath, 'rb') as f:
            with zipfile.ZipFile(f) as zip_ref:
                zip_ref.extractall(self._tempVzgFolderPath)

        print(f'{self._originVzgPath} unpacked!')

    def repack_vzg_file(self, outputVzgFilePath: str, imageParams: ImageParams):
        maxZPlane = self.read_dataset_z_planes_count()

        vzgRootFolder = os.listdir(self._tempVzgFolderPath)
        manifestExist = False
        for file in vzgRootFolder:
            if file in ('manifest.xml', 'manifest.json'):
                manifestExist = True
                if file == 'manifest.json':
                    self._add_cells_flag_to_manifest()
                break

        if not manifestExist:
            create_manifest(self._datasetName, self._tempVzgFolderPath, maxZPlane, imageParams)
            print('New manifest created')

        if os.path.exists(f'{outputVzgFilePath}.vzg'):
            os.remove(f'{outputVzgFilePath}.vzg')

        protocol, path_inside_fs = protocol_path_split(outputVzgFilePath)
        if protocol != Protocol.LOCAL:  # Protocol.S3 or Protocol.GCS
            tempNewVzgPath = os.path.join(self._tempBuildFolderPath, os.path.basename(outputVzgFilePath))
            shutil.make_archive(tempNewVzgPath, 'zip', self._tempVzgFolderPath)
            os.rename(f'{tempNewVzgPath}.zip', f'{tempNewVzgPath}.vzg')

            fs = filesystem_for_protocol(protocol)
            fs.put(f'{tempNewVzgPath}.vzg', f'{path_inside_fs}.vzg')
        else:
            shutil.make_archive(outputVzgFilePath, 'zip', self._tempVzgFolderPath)
            os.rename(f'{outputVzgFilePath}.zip', f'{outputVzgFilePath}.vzg')
        print('new vzg file created')

        if os.path.exists(self._tempBuildFolderPath):
            remove_tree(self._tempBuildFolderPath)
        print('temp files deleted')

    def _add_cells_flag_to_manifest(self):
        manifestPath = os.path.join(self._tempVzgFolderPath, 'manifest.json')
        with open(manifestPath, 'r') as f:
            manifestData = json.load(f)
            manifestData['Cells'] = True

        with open(manifestPath, 'w') as f:
            json.dump(manifestData, f, indent=4)

    def read_genes_info_array(self) -> dict:
        gene_info_path = os.path.join(self._tempVzgFolderPath, 'genes', 'genes_info_array.json')

        with open(gene_info_path, 'r') as f:
            gene_info_data = json.load(f)

        return gene_info_data
