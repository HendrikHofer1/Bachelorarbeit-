import unreal
import argparse
import sys
import os

test_identity_asset_name = 'KU_Test_Identity'


def run_import_takes_script(path_to_takes : str, storage_path : str):
    #führt das Skript create_capture_data_auto.py aus.
    from create_capture_data_auto import import_take_data_for_specified_device
    is_using_LLF_data = True
    #Die Pfade der erstellten CaptureData Objekte werden zurückgegeben.
    LLF_archive_takes = import_take_data_for_specified_device(path_to_takes, is_using_LLF_data, storage_path)

    return LLF_archive_takes
    
def run_create_identity_from_script(neutral_frames : list, capture_source_asset_path : str, asset_storage_location : str, identity_asset_name : str):
    #führt das Skript create_identity_for_performance_auto.py aus.
    from create_identity_for_performance_auto import create_identity_from_frame
    create_identity_from_frame(neutral_frames, capture_source_asset_path, asset_storage_location, identity_asset_name)

def run():
    
    print("Test")
    parser = argparse.ArgumentParser(prog=sys.argv[0], description="Create capture data sources from foorage imported to disk")
    parser.add_argument("--footage-path", type=str, required=True, help="An absolute path to a folder, containig footage for capture device")
    parser.add_argument("--storage-path-CD", type=str, required=False, help="A relative content path where the assets should be stored, e.g. /Game/MHA-Data/")
    parser.add_argument("--neutral-frames", nargs="*", type=int, required=True, help="Frame numbers that corresponds to neutral pose")
    parser.add_argument("--storage-path-MHI", type=str, required=False, help="A relative content path where the assets should be stored, e.g. /Game/MHA-Data/")

    args = parser.parse_args()
    path_to_footage = args.footage_path
    storage_location_CD = '/Game/' if args.storage_path_CD is None else args.storage_path_CD
    storage_location_MHI = '/Game/' if len(args.storage_path_MHI) == 0 else args.storage_path_MHI
    
    #Import the footage
    print('Running take import from script')
    LLF_archive_source_paths = run_import_takes_script(path_to_footage, storage_location_CD)
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    
    #Create an identity using hard-coded path to DNA test files
    print('Running identity creation from script for testing')
    run_create_identity_from_script(args.neutral_frames, LLF_archive_source_paths[0], storage_location_MHI, test_identity_asset_name)
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
   

if __name__ == "__main__":
    run()