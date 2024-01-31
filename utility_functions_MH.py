# Copyright Epic Games, Inc. All Rights Reserved.

# This script contains utility functions that could be used by other scripts in MetaHuman plugin content folder

import unreal
import os

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

def create_or_recreate_asset(in_asset_name, in_package_path, in_asset_class, in_factory):
    path_to_asset = os.path.join(in_package_path, in_asset_name)

    if unreal.EditorAssetLibrary.does_asset_exist(path_to_asset):
        print('Deleting an existing asset before creating a new one with the same name')
        unreal.EditorAssetLibrary.delete_asset(path_to_asset)

    created_asset = asset_tools.create_asset(asset_name=in_asset_name, package_path=in_package_path, 
                                           asset_class=in_asset_class, factory=in_factory)
    
    if created_asset is None:
        unreal.log_error("Error creating asset '{0}'".format(path_to_asset))
        exit()
    
    return created_asset

def get_or_create_asset(in_asset_name, in_package_path, in_asset_class, in_factory):
    asset_subsystem = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    path_to_asset = os.path.join(in_package_path, in_asset_name)

    asset = None
    if unreal.EditorAssetLibrary.does_asset_exist(path_to_asset):
        asset = asset_subsystem.load_asset(asset_path=path_to_asset)

    if asset is None:
        asset = asset_tools.create_asset(asset_name=in_asset_name, package_path=in_package_path,
                                         asset_class=in_asset_class, factory=in_factory)
    if asset is None:
        unreal.log_error("Error creating asset '{0}'".format(path_to_asset))
        exit()

    return asset