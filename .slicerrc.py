#make help as the default panel
findChildren(name="HelpAcknowledgementTabWidget")[0].currentIndex = 0

#disable interpolation of the volumes by default
def NoInterpolate(caller,event):
  for node in slicer.util.getNodes('*').values():
    if node.IsA('vtkMRMLScalarVolumeDisplayNode'):
      node.SetInterpolate(0)
slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent, NoInterpolate)

# Disable slice annotations persistently (after Slicer restarts)
settings = qt.QSettings()
settings.setValue('DataProbe/sliceViewAnnotations.enabled', 0)
