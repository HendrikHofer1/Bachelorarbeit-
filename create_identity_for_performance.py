# Copyright Epic Games, Inc. All Rights Reserved.

"""
This script loads a capture data source of type footage, creates an identity with a passed command line argument frame number
As promoted frame. Initializes contour data from the config and runs the tracking pipeline for that frame.
The data is then used to conform the template mesh. The back-end AutoRig service is invoked to retrieve a DNA, which is applied
To the skeletal mesh. At which point the identity is prepared for performance.

The user must be connected to AutoRig service prior to running this script.
In addition, a frame number for a neutral pose must be supplied as an argument to the script
Specified names and paths are for illustratory purpose only, and script should be modified accordingly
"""

import unreal
import argparse
import sys
import time

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

# Following hard-coded paths are used for demonstration purpose when running this script directly
test_identity_asset_name = 'KU_Test_Identity'

def prepare_identity_for_performance(identity_asset : unreal.MetaHumanIdentity):
   face: unreal.MetaHumanIdentityFace = identity_asset.get_or_create_part_of_class(unreal.MetaHumanIdentityFace)
   face.run_predictive_solver_training()
   print("Created Identity could now be used to process performance")

def process_autorig_service_response(dna_applied_success : bool):
    global global_identity_asset_name, global_identity_storage_location
    print("Cleaning up the delegate for '{0}'".format(global_identity_asset_name))

    identity_asset = unreal.load_asset(global_identity_storage_location + '/' + global_identity_asset_name)
    identity_asset.on_auto_rig_service_finished.remove_callable(process_autorig_service_response)
    global_identity_asset_name = ''
    if(dna_applied_success):
        prepare_identity_for_performance(identity_asset)
    else:
        unreal.log_error("Failed to retrieve the DNA from Autorig service")

def create_identity_from_frame(neutral_frames : list, capture_source_asset_path : str, asset_storage_location : str, identity_asset_name : str):

    global global_identity_asset_name, global_identity_storage_location
    global_identity_asset_name = identity_asset_name
    global_identity_storage_location = asset_storage_location

    if not unreal.EditorAssetLibrary.does_asset_exist(capture_source_asset_path):
        unreal.log_error(f"Could not locate Capture Data Source at provided location: {capture_source_asset_path}")

    capture_data_asset = unreal.load_asset(capture_source_asset_path)
    MetaHuman_identity_asset: unreal.MetaHumanIdentity = asset_tools.create_asset(asset_name=identity_asset_name, package_path=asset_storage_location, 
                                                                                  asset_class=unreal.MetaHumanIdentity, factory=unreal.MetaHumanIdentityFactoryNew())
    MetaHuman_identity_asset.get_or_create_part_of_class(unreal.MetaHumanIdentityFace)

    if not MetaHuman_identity_asset.is_logged_in_to_service():
        MetaHuman_identity_asset.log_in_to_auto_rig_service()
        
    face: unreal.MetaHumanIdentityFace = MetaHuman_identity_asset.get_or_create_part_of_class(unreal.MetaHumanIdentityFace)
    pose: unreal.MetaHumanIdentityPose = unreal.new_object(type=unreal.MetaHumanIdentityPose, outer=face)

    face.add_pose_of_type(unreal.IdentityPoseType.NEUTRAL, pose)
    pose.set_capture_data(capture_data_asset)

    pose.load_default_tracker()
    
    first_frame = True
    
    MetaHuman_identity_asset.set_blocking_processing(True)
   
    for i,nframe in enumerate(neutral_frames):
        frame, index = pose.add_new_promoted_frame()
        if first_frame:
            frame.is_front_view = True
            first_frame = False
        frame.set_navigation_locked(True)
        frame.frame_number = nframe

        if unreal.PromotedFrameUtils.initialize_contour_data_for_footage_frame(pose, frame) :
            image_path = unreal.PromotedFrameUtils.get_image_path_for_frame(capture_data_asset, pose.get_editor_property('camera'), nframe, True, pose.timecode_alignment)

            #Retreiving image from disk and storing it in an array
            image_size, local_samples = unreal.PromotedFrameUtils.get_promoted_frame_as_pixel_array_from_disk(image_path)

            if(image_size.x > 0 and image_size.y > 0) :
                # Make sure the pipeline is running synchronously with no progress indicators
                show_progress = False
                
                # Running tracking pipeline to get contour data for image retrieved from disk
                MetaHuman_identity_asset.start_frame_tracking_pipeline(local_samples, image_size.x, image_size.y, frame, show_progress)
                face.conform()

        else:
            unreal.log_error("Failed to initialize contour data. Please make sure valid frame is selected")
    
    
    print("Face has been conformed")
    body: unreal.MetaHumanIdentityBody = MetaHuman_identity_asset.get_or_create_part_of_class(unreal.MetaHumanIdentityBody)
    body.body_type_index = 3

    if(MetaHuman_identity_asset.is_logged_in_to_service()):
       print("Calling AutoRig service to create a DNA for identity")
       MetaHuman_identity_asset.on_auto_rig_service_finished.add_callable(process_autorig_service_response)
       add_to_MetaHuman_creator = False
       MetaHuman_identity_asset.create_dna_for_identity(add_to_MetaHuman_creator, log_only_no_dialogue)

    else:
          unreal.log_error("Please make sure you are logged in to MetaHuman service")


def create_identity_from_dna_file(path_to_dna_file : str, path_to_Json : str, asset_storage_location : str, identity_name : str) :
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    Metahuman_idenditiy_asset = asset_tools.create_asset(asset_name=identity_name, package_path=asset_storage_location, asset_class=unreal.MetaHumanIdentity, factory=unreal.MetaHumanIdentityFactoryNew())
    Metahuman_idenditiy_asset.get_or_create_part_of_class(unreal.MetaHumanIdentityFace)

    dna_type = unreal.DNADataLayer.ALL
    import_error: unreal.IdentityErrorCode = Metahuman_idenditiy_asset.import_dna_file(path_to_dna_file, dna_type, path_to_Json)
    if import_error == unreal.IdentityErrorCode.NONE:
        prepare_identity_for_performance(Metahuman_idenditiy_asset)
    else:
        unreal.log_error('Selected DNA and Json files are not compatible with this plugin')

def run():

   parser = argparse.ArgumentParser(prog=sys.argv[0], description="Test initializing and tracking promoted frame with contour data")
   parser.add_argument("--neutral-frame", nargs="*", type=int, required=True, help="Frame number that corresponds to neutral pose")
   parser.add_argument("--capture-data-path", type=str, required=True, help="An absolute or relative path to capture data asset")
   parser.add_argument("--storage-path", type=str, required=False, help="A relative content path where the assets should be stored, e.g. /Game/MHA-Data/")
   
   args = parser.parse_args()
   storage_location = '/Game/' if len(args.storage_path) == 0 else args.storage_path
   path_to_capture_data = args.capture_data_path

   create_identity_from_frame(args.neutral_frame, path_to_capture_data, storage_location, test_identity_asset_name)

if __name__ == "__main__":
   run()