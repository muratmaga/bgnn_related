#make help as the default panel
findChildren(name="HelpAcknowledgementTabWidget")[0].currentIndex = 0

#hide SLicer logo in module tab
slicer.util.findChild(slicer.util.mainWindow(), 'LogoLabel').visible = False

#collapse Data Probe tab by default to save space modules tab
slicer.util.findChild(slicer.util.mainWindow(), name='DataProbeCollapsibleWidget').collapsed = True

#disable interpolation of the volumes by default
def NoInterpolate(caller,event):
  for node in slicer.util.getNodes('*').values():
    if node.IsA('vtkMRMLScalarVolumeDisplayNode'):
      node.SetInterpolate(0)
slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent, NoInterpolate)

#Set the default Module to INHSTools
slicer.util.selectModule("INHSTools")

