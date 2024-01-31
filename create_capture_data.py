# Copyright Epic Games, Inc. All Rights Reserved.

"""
This script is used to import takes for specified device (either iPhone or HMC)
A temporary capture source asset is created and all the takes, the source is pointed to,
Are imported. As part of the import process all relevant assets are created and
A list of capture data source assets are returned. These capture source assets could
Be further used by identity creation or performance processing scripts
"""

import unreal
import argparse
import sys
import os

from utility_functions_MH import get_or_create_asset


def prepare_ingest_root_path(capture_source_name : str, storage_path : str) -> str:
    content_directory = unreal.SystemLibrary.get_project_content_directory()
    #Can't run os.path.join with a path that starts with '/'
    ingest_folder = storage_path.replace('/Game/', '')
    prepared_ingest_folder = os.path.join(content_directory, ingest_folder, "{0}_Ingested".format(capture_source_name))

    return unreal.Paths.normalize_directory_name(prepared_ingest_folder)

def prepare_asset_path(capture_source_name : str, storage_path : str) -> str:
    #Can't run os.path.join with a path that starts with '/'
    ingest_folder = storage_path.replace('/Game/', '')
    prepared_asset_folder = os.path.join('/Game', ingest_folder, "{0}_Ingested".format(capture_source_name))

    return unreal.Paths.normalize_directory_name(prepared_asset_folder)

def create_capture_data_assets_for_imported_takes(capture_source : unreal.MetaHumanCaptureSource, imported_takes : list, storage_path : str) -> list:
   
   created_capture_data_assets = []
   for take in imported_takes:
      take_info: unreal.MetaHumanTakeInfo = capture_source.get_take_info(take.take_index)
      package_path = prepare_asset_path(unreal.Paths.make_platform_filename(capture_source.get_name()), storage_path)
      new_asset_name = take_info.name + '-CD'
      capture_data_asset = get_or_create_asset(new_asset_name, package_path, unreal.FootageCaptureData, unreal.FootageCaptureDataFactoryNew())

      created_capture_data_assets.append(package_path + "/" + take_info.name + '-CD')
      views = []
      # Setting all relevant parameters for Capture Data
      for view in take.views:
         views_asset = unreal.FootageCaptureView()
         views_asset.depth_sequence = view.depth
         views_asset.depth_timecode = view.depth_timecode
         views_asset.depth_timecode_present = view.depth_timecode_present
         views_asset.depth_timecode_rate = view.depth_timecode_rate
         views_asset.image_sequence = view.video
         views_asset.image_timecode = view.video_timecode
         views_asset.image_timecode_present = view.video_timecode_present
         views_asset.image_timecode_rate = view.video_timecode_rate
         views.append(views_asset)
      
      capture_data_asset.views = views
      capture_data_asset.audio = take.audio
      capture_data_asset.audio_timecode = take.audio_timecode
      capture_data_asset.audio_timecode_present = take.audio_timecode_present
      capture_data_asset.audio_timecode_rate = take.audio_timecode_rate
      capture_data_asset.camera_calibration = take.camera_calibration

      capture_data_asset_metadata = capture_data_asset.get_editor_property("metadata")
      capture_data_asset_metadata.device_class = device_class_from_string(take_info.device_class.lower())
      capture_data_asset_metadata.height = take_info.resolution.y
      capture_data_asset_metadata.width = take_info.resolution.x
      capture_data_asset_metadata.frame_rate = take_info.frame_rate

   return created_capture_data_assets
      

def import_take_data_for_specified_device(path_to_takes : str, using_LLF_data : bool, storage_path : str) -> list:
    """"
    Importing footage, generating relevant assets as part of import process and
    Returning a list of created capture data assets
    """
    # Python API is calling a synchronous version of capture source that does not get stored as asset in content browser
    capture_source = unreal.MetaHumanCaptureSourceSync()
    capture_source_type = unreal.MetaHumanCaptureSourceType.LIVE_LINK_FACE_ARCHIVES if using_LLF_data == True else unreal.MetaHumanCaptureSourceType.HMC_ARCHIVES
    capture_source.set_editor_property('capture_source_type', capture_source_type)
    dir_path = unreal.DirectoryPath()
    dir_path.set_editor_property("path", path_to_takes)
    capture_source.set_editor_property('storage_path', dir_path)
    capture_data_asset_list = []

    if capture_source.can_startup():
        capture_source.startup()

        # Populating the list of available takes for import at the specified location
        takes = capture_source.refresh()
        take_indices = prepare_takes_for_ingest(takes)

        capture_source_asset_name = unreal.Paths.make_platform_filename(capture_source.get_name())
        capture_source_target_ingest_directory = prepare_ingest_root_path(capture_source_asset_name, storage_path)
        capture_source_target_asset_directory = prepare_asset_path(capture_source_asset_name, storage_path)

        capture_source.set_target_path(capture_source_target_ingest_directory, capture_source_target_asset_directory)
        # Running the import process for all takes in a specified location
        imported_takes = capture_source.get_takes(take_indices)
        capture_data_asset_list = create_capture_data_assets_for_imported_takes(capture_source, imported_takes, storage_path)

        capture_source.shutdown()
        
    else:
        unreal.log_error(f"Failed to import footage from {path_to_takes}")

    return capture_data_asset_list


def prepare_takes_for_ingest(takes : unreal.Array[unreal.MetaHumanTakeInfo]) -> unreal.Array[int]:
    take_indices = unreal.Array(int)

    for take_info in takes:
        take_index = take_info.get_editor_property('index')
        take_indices.append(take_index)

    return take_indices


def device_class_from_string(device_name_string: str) -> unreal.FootageDeviceClass:
    """Utility for determining the Footage Device Class from the string"""
    _str_to_device = {
	    'iphone 11': unreal.FootageDeviceClass.I_PHONE11_OR_EARLIER,	# iPhone 11 or earlier
	    'iphone 12': unreal.FootageDeviceClass.I_PHONE12,			    # iPhone 12
	    'iphone 13': unreal.FootageDeviceClass.I_PHONE13,			    # iPhone 13
	    'iphone 14': unreal.FootageDeviceClass.I_PHONE14_OR_LATER,		# iPhone 14 or later
	    'm1':        unreal.FootageDeviceClass.OTHERI_OS_DEVICE,		# Other iOS device
	    'hmc':       unreal.FootageDeviceClass.STEREO_HMC,			    # Stereo HMC
    }
    # check if the key str is part of the filename
    for k, v in _str_to_device.items():
        if k in device_name_string:
            return v
    return unreal.FootageDeviceClass.UNSPECIFIED


def run():

   parser = argparse.ArgumentParser(prog=sys.argv[0], description="Create capture data sources from foorage imported to disk")
   parser.add_argument("--footage-path", type=str, required=True, help="An absolute path to a folder, containig footage for capture device")
   parser.add_argument("--using-livelinkface-data", action="store_true", default=False, help="Set if data comes from LiveLinkFace Archive, otherwise data will be treated as if it comes from HMC")
   parser.add_argument("--storage-path", type=str, required=False, help="A relative content path where the assets should be stored, e.g. /Game/MHA-Data/")

   args = parser.parse_args()
   path_to_footage = args.footage_path
   using_LLF_data :bool = args.using_livelinkface_data
   storage_location = '/Game/' if args.storage_path is None else args.storage_path

   import_take_data_for_specified_device(path_to_footage, using_LLF_data, storage_location)
   

if __name__ == "__main__":
    run()