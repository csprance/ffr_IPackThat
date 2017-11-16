#!/usr/bin/env python

import	lx
import	lxifc
import	lxu.command
import	lxu.select
import	subprocess
import	os

class IPackThat_Cmd (lxu.command.BasicCommand):
	def __init__ (self):
		lxu.command.BasicCommand.__init__ (self)

		self.scrp_svc = lx.service.ScriptSys ()
		self.sel_svc = lx.service.Selection ()

	def cmd_Interact (self):
		pass

	def cmd_UserName (self):
 		return 'Go IPackThat'

 	def cmd_Desc (self):
 		return 'Send mesh to IPackThat.'

 	def cmd_Tooltip (self):
 		return 'Send mesh to IPackThat.'

 	def cmd_Help (self):
 		return 'http://www.farfarer.com/'

	def basic_ButtonName (self):
		return 'Go IPackThat'

	def cmd_Flags (self):
		return lx.symbol.fCMD_UNDO

	def basic_Enable (self, msg):
		return True

	# Validate the path to IPackThat is good.
	def validIPackThatPath (self, ipackthat_exe_path):
		return ((ipackthat_exe_path != None) and os.path.lexists (ipackthat_exe_path) and (os.path.splitext (ipackthat_exe_path)[1].lower () == '.exe'))

	def getUVSelection (self):
		uv_selection = []
		vmap_pkt_trans = lx.object.VMapPacketTranslation (self.sel_svc.Allocate (lx.symbol.sSELTYP_VERTEXMAP))
		sel_type_vmap = self.sel_svc.LookupType (lx.symbol.sSELTYP_VERTEXMAP)

		for i in xrange(self.sel_svc.Count (sel_type_vmap)):
			pkt = self.sel_svc.ByIndex (sel_type_vmap, i)
			if vmap_pkt_trans.Type (pkt) == lx.symbol.i_VMAP_TEXTUREUV:
				uv_selection.append (vmap_pkt_trans.Name (pkt))
		return uv_selection

	# Set the path to IPackThat in a user variable.
	def setIPackThatPath (self, ipackthat_exe_path):
		if self.validIPackThatPath (ipackthat_exe_path):
			try:
				lx.eval ('!!user.defNew name:ipackthat_path type:string life:config')
			except:
				pass

			try:
				lx.eval ('!!user.value ipackthat_path {%s}' % ipackthat_exe_path)
			except:
				pass
			
			return (lx.eval1 ('user.value ipackthat_path ?') == ipackthat_exe_path)
		return False

	# Ask the user for the path to IPackThat.
	def findIPackThatPath (self):
		default_path = 'D:\\SteamLibrary\\steamapps\\common\\IPackThat\\IPackThat.exe'
		if self.setIPackThatPath (default_path):
			return True
		else:
			try:
				lx.eval ('dialog.setup fileOpen')
				lx.eval ('dialog.title "Select IPackThat executable file"')
				lx.eval ('dialog.fileTypeCustom format:exe username:{EXE} loadPattern:{*.exe} saveExtension:exe')
				if self.modo_ver == 801:
					lx.eval ('+dialog.open')
				else:
					lx.eval ('dialog.open')
				ipackthat_exe_path = lx.eval1 ('dialog.result ?')
			except:
				pass
			else:
				if self.setIPackThatPath (ipackthat_exe_path):
					return True

		lx.out ('Failed to define path to IPackThat.')
		return False

	def recurseToFindFBXMeshes (self, fbx_item, fbx_meshes, mesh_items):
		fbx_item_child_count = fbx_item.SubCount ()
		for child_index in xrange (fbx_item_child_count):
			child = fbx_item.SubByIndex (child_index)
			for x, mesh_item in enumerate (mesh_items):
				if child.Name () == mesh_item.UniqueName ():
					fbx_meshes[x] = child
			self.recurseToFindFBXMeshes (child, fbx_meshes, mesh_items)

	def getUserValue (self, name):
		try:
			valueObj = self.scrp_svc.UserValueLookup (name)
		except:
			return None
		
		itype = valueObj.Type ()
		if itype == lx.symbol.i_TYPE_INTEGER:
			return valueObj.GetInt ()
		elif itype == lx.symbol.i_TYPE_STRING:
			return valueObj.GetString ()
		elif itype == lx.symbol.i_TYPE_FLOAT:
			return valueObj.GetFlt ()

	def storeFBXSettings (self):
		FBX_USERVALUE_PREFIX	= 'sceneio.fbx.save.'
		FBX_USERVALUE_COMMAND	= 'user.value ' + FBX_USERVALUE_PREFIX
		
		fbxSettings = {}
		
		for x in xrange (self.scrp_svc.UserValueCount ()):
			uval = self.scrp_svc.UserValueByIndex (x)
			name = uval.Name ()
			if name.startswith ('sceneio.fbx.save.'):
				fbxSettings[name] = self.getUserValue (name)
		
		return fbxSettings
	
	def restoreFBXSettings (self, fbxSettings):
		for name, value in fbxSettings.items():
			lx.eval ('user.value %s %s' % (name, value))

	def basic_Execute (self, msg, flags):

		# MODO version checks. Different versions have different FBX options.
		self.modo_ver = int(lx.eval ('query platformservice appversion ?'))
		if self.modo_ver < 801:
			lx.out ('Requires Modo 801 or newer.')
			return

		# Get the selected UV names.
		selected_uv_names = self.getUVSelection ()
		if len (selected_uv_names) == 0:
			lx.out ('No UV maps selected.')
			return

		# Grab the active layer.
		layer_svc = lx.service.Layer ()
		layer_scan = lx.object.LayerScan (layer_svc.ScanAllocate (lx.symbol.f_LAYERSCAN_ACTIVE))
		if not layer_scan.test ():
			lx.out ('Layerscan failed.')
			return

		# Early out if there are no active layers.
		layer_count = layer_scan.Count ()
		if layer_count <= 0:
			lx.out ('No active layers.')
			return

		# Grab the relevant meshes and UV maps.
		mesh_items = []
		mesh_uvs = []
		for layer_idx in xrange (layer_count):
			mesh_item = lx.object.Item (layer_scan.MeshItem (layer_idx))
			if not mesh_item.test ():
				lx.out ('Failed to get mesh item of layer %s.' % layer_idx)
				continue

			mesh_name = mesh_item.UniqueName ()
			
			mesh = lx.object.Mesh (layer_scan.MeshBase (layer_idx))
			if not mesh.test ():
				lx.out ('Failed to get mesh of %s.' % mesh_name)
				continue

			# Get the selected UV maps that exist on this model.
			meshmap = lx.object.MeshMap (mesh.MeshMapAccessor ())
			if not meshmap.test ():
				lx.out ('Failed to get meshmap accessor of %s.' % mesh_name)
				continue

			selected_uv_names_mesh = []
			for uv_map in selected_uv_names:
				try:
					meshmap.SelectByName (lx.symbol.i_VMAP_TEXTUREUV, uv_map)
				except:
					pass
				else:
					selected_uv_names_mesh.append (uv_map)

			if len (selected_uv_names_mesh) == 0:
				lx.out ('%s does not have any of the selected UV maps on it.' % mesh_name)
				continue
				
			mesh_items.append (mesh_item)
			mesh_uvs.append (selected_uv_names_mesh)

		layer_scan.Apply ()

		# Select the meshes.
		for x, mesh_item in enumerate(mesh_items):
			if x == 0:
				lx.eval ('select.subItem %s set mesh 0 0' % mesh_item.Ident ())
			else:
				lx.eval ('select.subItem %s add mesh 0 0' % mesh_item.Ident ())

		# Get IPackThat executable path.
		ipackthat_path = None
		try:
			ipackthat_path = lx.eval1 ('!!user.value ipackthat_path ?')
		except:
			if not self.findIPackThatPath ():
				return
		else:
			if not self.validIPackThatPath (ipackthat_path):
				if not self.findIPackThatPath ():
					return
				else:
					ipackthat_path = lx.eval1 ('!!user.value ipackthat_path ?')

		if ipackthat_path is None:
			lx.out ('Invalid IPackThat path.')
			return

		# Store user's FBX preferences for restoring later.
		fbxSettings = self.storeFBXSettings ()

		# Apply FBX settings we want to use for IPackThat.
		# Essentially disabling everything except geometry and setting export to selection.
		# Also picking FBX2013, just because that should ensure things export smoothly.
		lx.eval ('user.value sceneio.fbx.save.format 2')
		lx.eval ('user.value sceneio.fbx.save.exportType 1')
		lx.eval ('user.value sceneio.fbx.save.geometry 1')
		
		lx.eval ('user.value sceneio.fbx.save.exportToASCII 0')
		lx.eval ('user.value sceneio.fbx.save.animationOnly 0')
		lx.eval ('user.value sceneio.fbx.save.cameras 0')
		lx.eval ('user.value sceneio.fbx.save.lights 0')
		lx.eval ('user.value sceneio.fbx.save.materials 0')
		lx.eval ('user.value sceneio.fbx.save.polygonParts 0')
		lx.eval ('user.value sceneio.fbx.save.selectionSets 0')
		lx.eval ('user.value sceneio.fbx.save.smoothingGroups 0')
		lx.eval ('user.value sceneio.fbx.save.morphMaps 0')
		lx.eval ('user.value sceneio.fbx.save.animation 0')
		lx.eval ('user.value sceneio.fbx.save.sampleAnimation 0')
		if self.modo_ver > 900:
			try:
				lx.eval1 ('user.value sceneio.fbx.save.tangentsBitangents 0')
			except RuntimeError:
				pass
		if self.modo_ver > 1000 and self.modo_ver <= 1011:
			try:
				lx.eval ('user.value sceneio.fbx.save.triangulate 0')
				lx.eval ('user.value sceneio.fbx.save.meshSmoothing 0')
			except RuntimeError:
				pass
		if self.modo_ver >= 1012:
			try:
				lx.eval ('user.value sceneio.fbx.save.surfaceRefining 0')
			except RuntimeError:
				pass

		# Export the FBX.
		try:
			lx.eval ('dialog.setup fileSave')
			lx.eval ('dialog.title "Save FBX file for IPackThat"')
			lx.eval ('dialog.fileType scene2')
			lx.eval ('dialog.fileSaveFormat fbx format')
			if self.modo_ver == 801:
				lx.eval ('+dialog.open')
			else:
				lx.eval ('dialog.open')
			fbx_export_path = lx.eval1 ('dialog.result ?')
		except:
			lx.out ('Didn\'t save FBX for IPackThat.')
			return
		else:
			if fbx_export_path == None:
				lx.out ('Didn\'t save FBX for IPackThat.')
				return
			else:
				fbx_export_path = os.path.splitext (fbx_export_path)[0] + '.fbx'
				fbx_file_name = os.path.splitext (os.path.basename (fbx_export_path))[0]

		lx.eval ('scene.saveAs "%s" fbx true' % fbx_export_path)
		fbx_save_time = os.path.getmtime (fbx_export_path)

		# Restore the FBX preferences.
		self.restoreFBXSettings (fbxSettings)

		# Call IPackThat.
		proc = subprocess.Popen([ipackthat_path, fbx_export_path], stdout=subprocess.PIPE)
		stdout, stderr = proc.communicate()
		rc = proc.returncode

		if rc != 0:
			# IPackThat crashed or threw an error.
			lx.out ('IPackThat crashed.')
			lx.out ('Standard Output: %s' % stdout)
			lx.out ('Error Output: %s' % stderr)
		else:
			# Get the modified time of the export file.
			fbx_load_time = 0
			if os.path.lexists (fbx_export_path):
				fbx_load_time = os.path.getmtime (fbx_export_path)

			# User has likely saved over the old file.
			if fbx_load_time > fbx_save_time:
				if self.modo_ver > 1000:
					lx.eval ('!!loaderOptions.fbx mergeWithExistingItems:false loadGeometry:true loadNormals:false loadMeshSmoothing:false loadBlendShapes:false loadPolygonParts:false loadSelectionSets:false loadMaterials:false invertMatTranAmt:false useMatTranColAsTranAmt:false changeTextureEffect:false loadCameras:false loadLights:false loadAnimation:false loadSampleAnimation:false loadSampleAnimationRate:0 globalScalingFactor:1.0 importUnits:0')
				else:
					lx.eval ('!!loaderOptions.fbx mergeWithExistingItems:false loadGeometry:true loadNormals:false loadMeshSmoothing:false loadBlendShapes:false loadPolygonParts:false loadSelectionSets:false loadMaterials:false invertMatTranAmt:false useMatTranColAsTranAmt:false loadCameras:false loadLights:false loadAnimation:false loadSampleAnimation:false loadSampleAnimationRate:0')
				lx.eval ('!!scene.open "%s" import' % fbx_export_path)
			else:
				try:
					lx.eval ('dialog.setup fileOpen')
					lx.eval ('dialog.title "Load FBX file from IPackThat"')
					lx.eval ('dialog.fileType scene2')
					if self.modo_ver == 801:
						lx.eval ('+dialog.open')
					else:
						lx.eval ('dialog.open')
					fbx_import_path = lx.eval1 ('dialog.result ?')
				except:
					lx.out ('Failed to load scene with new UVs.')
					return
				else:
					if fbx_import_path == None:
						return
					else:
						fbx_file_name = os.path.splitext (os.path.basename (fbx_import_path))[0]
						if self.modo_ver > 1000:
							lx.eval ('!!loaderOptions.fbx mergeWithExistingItems:false loadGeometry:true loadNormals:false loadMeshSmoothing:false loadBlendShapes:false loadPolygonParts:false loadSelectionSets:false loadMaterials:false invertMatTranAmt:false useMatTranColAsTranAmt:false changeTextureEffect:false loadCameras:false loadLights:false loadAnimation:false loadSampleAnimation:false loadSampleAnimationRate:0 globalScalingFactor:1.0 importUnits:0')
						else:
							lx.eval ('!!loaderOptions.fbx mergeWithExistingItems:false loadGeometry:true loadNormals:false loadMeshSmoothing:false loadBlendShapes:false loadPolygonParts:false loadSelectionSets:false loadMaterials:false invertMatTranAmt:false useMatTranColAsTranAmt:false loadCameras:false loadLights:false loadAnimation:false loadSampleAnimation:false loadSampleAnimationRate:0')
						lx.eval ('!scene.open "%s" import' % fbx_import_path)

			scene = lxu.select.SceneSelection ().current ()
			scn_svc = lx.service.Scene ()
			group_type = scn_svc.ItemTypeLookup (lx.symbol.sITYPE_GROUPLOCATOR)

 			fbx_group_index = -2
			fbx_group = None
 			group_ident = None
 			item_ident = None
			
			# Find the newly imported FBX scene.
			group_count = scene.ItemCount (group_type)
			for i in reversed (xrange (group_count)):
				group = scene.ItemByIndex (group_type, i)
				if group.Name () == fbx_file_name:
					group_index = group.UniqueIndex ()
					if group_index > fbx_group_index:
						fbx_group_index = group_index
						fbx_group = group

			if fbx_group is not None:
				
				# Find the newly imported FBX versions of our original meshes.
				fbx_meshes = [None] * len(mesh_items)
				self.recurseToFindFBXMeshes (fbx_group, fbx_meshes, mesh_items)
				
				# Copy over the UVs.
				for fbx_mesh, mesh_item, mesh_uv in zip(fbx_meshes, mesh_items, mesh_uvs):
					if fbx_mesh is not None:
						fbx_ident = fbx_mesh.Ident ()
						mesh_ident = mesh_item.Ident ()
						for uv_map in mesh_uv:
							lx.eval ('select.subItem %s set mesh 0 0' % fbx_ident)
							
							try:
								lx.eval ('select.vertexMap %s txuv replace' % uv_map)
							except:
								continue
							else:
								try:
									lx.eval ('select.type polygon')
									lx.eval ('select.all')
									lx.eval ('uv.copy')

									lx.eval ('select.subItem %s set mesh 0 0' % mesh_ident)
									lx.eval ('select.vertexMap %s txuv replace' % uv_map)
								except:
									continue
								else:
									try:
										lx.eval ('select.type polygon')
										lx.eval ('select.all')
									
										if self.modo_ver > 801:
											lx.eval ('uv.paste selection')
										else:
											lx.eval ('uv.paste')
									except:
										continue

				# Delete the imported FBX scene.
				if self.modo_ver > 1009:
					lx.eval ('!!item.delete child:1 item:%s' % fbx_group.Ident())
				else:
					lx.eval ('select.subItem %s set groupLocator 0 0' % fbx_group.Ident ())
					lx.eval ('!!item.delete mask:groupLocator child:1')

				# Reselect the original mesh and UVs.
				for mesh_item in mesh_items:
					lx.eval ('select.subItem %s add mesh 0 0' % mesh_item.Ident ())
				for idx, uv_map in enumerate (selected_uv_names_mesh):
					if idx == 0:
						lx.eval ('select.vertexMap %s txuv replace' % uv_map)
					else:
						lx.eval ('select.vertexMap %s txuv add' % uv_map)
				lx.eval ('select.drop polygon')

lx.bless (IPackThat_Cmd, 'ffr.IPackThat')
