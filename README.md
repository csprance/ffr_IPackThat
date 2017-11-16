# Modo <-> IPackThat.
> A script to help get UVs to/from IPackThat.

It's pretty simple to use, hopefully.
Extract this into the "Kits" folder in your modo content directory, restart MODO - it should work with 801 and newer.

To use it:
- Select the meshes and UV maps you want to pack.
- Click the button or run the command ffr.IPackThat
- The script will ask you (once) to find the path to IPackThat (although if it's already installed in the default Steam directory of C:\Program Files (x86)\Steam\SteamApps\common\IPackThat\IPackThat.exe it'll run straight from there). It gets saved in a user variable after that for subsequent runs.
- The script will then ask you to save an FBX file, then it will fire up IPackThat and load the mesh.
- Do your packing in IPackThat until you're happy with it.
- Save back out from IPackThat over the top of the FBX file you sent to it.
- Close IPackThat.
- Once IPackThat is closed, the script will kick back in and copy over the UVs from your packed version.
- If you save elsewhere, the script will ask you to find the new FBX file you saved from IPackThat instead, then it'll load it in and copy the UVs over.

This is a bit hacky, so it's probably a good idea to save your scene before running this, just in case.