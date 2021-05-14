import SimpleITK as sitk
import sitkUtils
import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import numpy as np
import string

import SampleData

#
# INHSTools
#
#define global variable 
labs = os.environ.get('labs','unknown_lab')

class INHSTools(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "INHSTools" # TODO make this more human readable by adding spaces
    self.parent.categories = ["SlicerMorph.SlicerMorph Labs"]
    self.parent.dependencies = []
    self.parent.contributors = ["Murat Maga (UW), Sara Rolfe (UW)"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
This module imports an image database (csv file) from which individual fish images from INHS collection can be loaded into 3D Slicer for landmarking.
<ol> 
<li>Navigate to <b>/segmented</b> folder, and then load the metadata.csv file in by clicking the <b>Load Table</b></li>
<li>Click on the fish filename from the table and hit <b>Import Image</b></li>
<li>Set the scale of the image (INHS DB only) to 1, 1, 1. Remember to adjust the field of view to bring the fish back to view. </li>
<li>If necessary flip the image along the X-axis to create a left-facing fish. </li>
<li>Use the fiducials markup to digitize the landmarks in the sequence agreed. You can use the <b>Pop up Markups</b> button to bring the Marksup module as a separate window.</li> 
<li>Once digitization is done, hit the <b>Export Landmarks</b> button to save the 
landmarks into the correct output folder automatically. This will remove the fish from the table view</li>
<li>You can now start the next unprocessed specimen</li>
</ol> 
"""
    self.parent.acknowledgementText = """
This module was developed by Sara Rolfe and Murat Maga, for the NSF HDR  grant, "Biology Guided Neural Networks" (Award Number: 1939505).
https://www.nsf.gov/awardsearch/showAward?AWD_ID=1939505&HistoricalAwards=false  
""" 

#
# INHSToolsWidget
#

class INHSToolsWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  def assignLayoutDescription(self, table):
    customLayout = """
    <layout type="vertical" split="true">
      <item>
       <view class="vtkMRMLSliceNode" singletontag="Red">
        <property name="orientation" action="default">Axial</property>
        <property name="viewlabel" action="default">R</property>
        <property name="viewcolor" action="default">#F34A33</property>
       </view>
      </item>
      <item>
       <view class="vtkMRMLTableViewNode" singletontag="TableViewerWindow_1">
         <property name=\"viewlabel\" action=\"default\">T</property>"
       </view>
      </item>
    </layout>
    """
    
    customLayoutId=701

    layoutManager = slicer.app.layoutManager()
    layoutManager.layoutLogic().GetLayoutNode().AddLayoutDescription(customLayoutId, customLayout)                                         

    # Switch to the new custom layout 
    layoutManager.setLayout(customLayoutId)
    
    # Select table in viewer
    slicer.app.applicationLogic().GetSelectionNode().SetReferenceActiveTableID(table.GetID())
    slicer.app.applicationLogic().PropagateTableSelection()
    
  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Instantiate and connect widgets ...
    #
    # Input/Export Area
    #
    IOCollapsibleButton = ctk.ctkCollapsibleButton()
    IOCollapsibleButton.text = "Input and Export"
    self.layout.addWidget(IOCollapsibleButton)

    # Layout within the dummy collapsible button
    #IOFormLayout = qt.QFormLayout(IOCollapsibleButton)
    IOFormLayout= qt.QGridLayout(IOCollapsibleButton)
    
    #
    # Table volume selector
    #
    tableSelectorLabel=qt.QLabel("Input table: ")
    self.tableSelector = ctk.ctkPathLineEdit()
    self.tableSelector.nameFilters=["*.csv"]
    self.tableSelector.setToolTip( "Select table with filenames to process" )
    
    self.selectorButton = qt.QPushButton("Load Table")
    self.selectorButton.toolTip = "Load the table of image filenames to process"
    self.selectorButton.enabled = False
    IOFormLayout.addWidget(tableSelectorLabel,1,1)
    IOFormLayout.addWidget(self.tableSelector,1,2)
    IOFormLayout.addWidget(self.selectorButton,1,3)
    
    #
    # Output path selector
    #
    outputDirSelectorLabel=qt.QLabel("Output Path: ")
    self.outputDirSelector = ctk.ctkPathLineEdit()
    self.outputDirSelector.filters = ctk.ctkPathLineEdit.Dirs
    self.outputDirSelector.currentPath = slicer.app.cachePath
    self.outputDirSelector.setToolTip( "Select directory for output" )
    IOFormLayout.addWidget(outputDirSelectorLabel,2,1,1,1)
    IOFormLayout.addWidget(self.outputDirSelector,2,2,1,2)
    
    #
    # Import Volume Button
    #
    self.importVolumeButton = qt.QPushButton("Import image")
    self.importVolumeButton.toolTip = "Import the image selected in the table"
    self.importVolumeButton.enabled = False
    IOFormLayout.addWidget(self.importVolumeButton,3,1,1,3)
    
    #
    # Image editing Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Image Editing"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)
    
    #
    # input volume selector
    #
    self.volumeSelector = slicer.qMRMLNodeComboBox()
    self.volumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode", "vtkMRMLVectorVolumeNode" ]
    self.volumeSelector.selectNodeUponCreation = True
    self.volumeSelector.addEnabled = True
    self.volumeSelector.removeEnabled = True
    self.volumeSelector.noneEnabled = True
    self.volumeSelector.showHidden = False
    self.volumeSelector.showChildNodeTypes = False
    self.volumeSelector.renameEnabled = True
    self.volumeSelector.setMRMLScene( slicer.mrmlScene )
    self.volumeSelector.setToolTip( "Select volume to resample" )
    parametersFormLayout.addRow("Input Volume: ", self.volumeSelector)
    
    #
    # Flip X-axis Button
    #
    self.flipXButton = qt.QPushButton("Flip X-axis")
    self.flipXButton.toolTip = "Flip the loaded volume across the X-axis"
    self.flipXButton.enabled = False
    parametersFormLayout.addRow(self.flipXButton)
    
    #
    # Flip Y-axis Button
    #
    self.flipYButton = qt.QPushButton("Flip Y-axis")
    self.flipYButton.toolTip = "Flip the loaded volume across the Y-axis"
    self.flipYButton.enabled = False
    parametersFormLayout.addRow(self.flipYButton)
    
    #
    # Flip Z-axis Button
    #
    self.flipZButton = qt.QPushButton("Flip Z-axis")
    self.flipZButton.toolTip = "Flip the loaded volume across the x-axis"
    self.flipZButton.enabled = False
    parametersFormLayout.addRow(self.flipZButton)
    
    #
    # Annotations area
    #
    annotationsButton = ctk.ctkCollapsibleButton()
    annotationsButton.text = "Annotations"
    self.layout.addWidget(annotationsButton)
    annotationsLayout= qt.QGridLayout(annotationsButton)
    
    # Set up tabs to split workflow
    tabsWidget = qt.QTabWidget()
    landmarkTab = qt.QWidget()
    landmarkTabLayout = qt.QFormLayout(landmarkTab)
    segmentTab = qt.QWidget()
    segmentTabLayout = qt.QFormLayout(segmentTab)

    tabsWidget.addTab(segmentTab, "Segment")
    tabsWidget.addTab(landmarkTab, "Landmark")
    annotationsLayout.addWidget(tabsWidget)

    #
    # Markups Launch Button
    #
    self.launchMarkupsButton = qt.QPushButton("Start landmarking")
    self.launchMarkupsButton.toolTip = "Pop up the markups view for placing landmarks"
    self.launchMarkupsButton.enabled = False
    landmarkTabLayout.addRow(self.launchMarkupsButton)
    
    #
    # Export Landmarks Button
    #
    self.exportLandmarksButton = qt.QPushButton("Export landmarks")
    self.exportLandmarksButton.toolTip = "Export landmarks placed on the selected image"
    self.exportLandmarksButton.enabled = False
    landmarkTabLayout.addRow(self.exportLandmarksButton)
    
    #
    # Initiate Segmentation
    #
    self.startSegmentationButton = qt.QPushButton("Start segmenation")
    self.startSegmentationButton.toolTip = "Initialize segmentation and view Segment Editor"
    self.startSegmentationButton.enabled = False
    segmentTabLayout.addRow(self.startSegmentationButton)
    
    #
    # Export Segmentation
    #
    self.exportSegmentationButton = qt.QPushButton("Export segmenation")
    self.exportSegmentationButton.toolTip = "Export segmentation as a model"
    self.exportSegmentationButton.enabled = False
    segmentTabLayout.addRow(self.exportSegmentationButton)
    
    # connections
    #self.applySpacingButton.connect('clicked(bool)', self.onApplySpacingButton)
    self.flipXButton.connect('clicked(bool)', self.onFlipX)
    self.flipYButton.connect('clicked(bool)', self.onFlipY)
    self.flipZButton.connect('clicked(bool)', self.onFlipZ)
    self.selectorButton.connect('clicked(bool)', self.onLoadTable)
    self.volumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.tableSelector.connect("validInputChanged(bool)", self.onSelectTablePath)
    self.importVolumeButton.connect('clicked(bool)', self.onImportVolume)
    self.exportLandmarksButton.connect('clicked(bool)', self.onExportLandmarks)
    self.launchMarkupsButton.connect('clicked(bool)', self.onLaunchMarkups)
    self.startSegmentationButton.connect('clicked(bool)', self.onStartSegmentation)
    self.exportSegmentationButton.connect('clicked(bool)', self.onExportSegmentation)

    
    # Add vertical spacer
    self.layout.addStretch(1)

    # Refresh Apply button state
    self.onSelect()
    
  def cleanup(self):
    pass
  
  def onStartSegmentation(self):
    logic = INHSToolsLogic()
    self.segmentationNode = logic.initializeSegmentation(self.volumeNode)
    self.exportSegmentationButton.enabled = True
    slicer.util.selectModule(slicer.modules.segmenteditor)
  
  def onExportSegmentation(self):
    if hasattr(self,'segmentationNode'):
      segmentationName = os.path.splitext(self.activeCellString)[0]
      segmentationOutput = os.path.join(self.outputDirSelector.currentPath, self.currentSpecimenName +'.nrrd')
      slicer.util.saveNode(self.segmentationNode, segmentationOutput)
      self.outputLabelmapNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
      slicer.modules.segmentations.logic().ExportVisibleSegmentsToLabelmapNode(self.segmentationNode, self.outputLabelmapNode)
      tifOutput = os.path.join(self.outputDirSelector.currentPath, self.currentSpecimenName +'.tif')
      slicer.util.saveNode(self.outputLabelmapNode, tifOutput)
      self.updateTableAndGUI()
    else:
      logging.debug("No valid segmentation to export.")
      
  def onLaunchMarkups(self):
    self.fiducialNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", 'F')
    markups_widget = slicer.modules.markups.createNewWidgetRepresentation()
    markups_widget.setMRMLScene(slicer.mrmlScene)
    markups_widget.show()
    markups_widget.enter()
    self.exportLandmarksButton.enabled = True
    
  def updateStatus(self, index, string):
    # refresh table from file, update the status column, and save 
    name = self.fileTable.GetName()
    slicer.mrmlScene.RemoveNode(self.fileTable)
    self.fileTable = slicer.util.loadNodeFromFile(self.tableSelector.currentPath, 'TableFile')
    self.fileTable.SetLocked(True)
    self.fileTable.SetName(name)
    logic = INHSToolsLogic()
    #logic.hideCompletedSamples(self.fileTable)
    statusColumn = self.fileTable.GetTable().GetColumnByName('Status')
    statusColumn.SetValue(index-1, string)
    #set the user to the lab based on an environment variable
    userColumn = self.fileTable.GetTable().GetColumnByName('User')
    userColumn.SetValue(index-1, labs)
    self.fileTable.GetTable().Modified() # update table view
    slicer.util.saveNode(self.fileTable, self.tableSelector.currentPath)
    
  def onSelectTablePath(self):
    if(self.tableSelector.currentPath):
      self.selectorButton.enabled = True
    else:
      self.selectorButton.enabled  = False
  
  def onLoadTable(self):
    if hasattr(self,'fileTable'):
      tableName = self.fileTable.GetName()
      slicer.mrmlScene.RemoveNode(self.fileTable)  
      self.fileTable = slicer.util.loadNodeFromFile(self.tableSelector.currentPath, 'TableFile')
      self.fileTable.SetName(tableName)
    else:
      self.fileTable = slicer.util.loadNodeFromFile(self.tableSelector.currentPath, 'TableFile')
    if bool(self.fileTable):
      logic = INHSToolsLogic()
      logic.checkForStatusColumn(self.fileTable, self.tableSelector.currentPath) # if not present adds and saves to file
      self.importVolumeButton.enabled = True
      self.assignLayoutDescription(self.fileTable)
      #logic.hideCompletedSamples(self.fileTable)
      self.fileTable.SetLocked(True)
      self.fileTable.GetTable().Modified() # update table view
    else:
      self.importButton.enabled = False
  
  def onSelect(self):
    if bool(self.volumeSelector.currentNode()):  
      self.flipXButton.enabled = True
      self.flipYButton.enabled = True
      self.flipZButton.enabled = True
    else:
      #self.applySpacingButton.enabled = False
      self.flipXButton.enabled = False
      self.flipYButton.enabled = False
      self.flipZButton.enabled = False  

  def onFlipX(self):
    logic = INHSToolsLogic()
    matrix = vtk.vtkMatrix4x4()
    matrix.SetElement(0, 0, -1)
    logic.flip(self.volumeSelector.currentNode(), matrix)
  
  def onFlipY(self):
    logic = INHSToolsLogic()
    matrix = vtk.vtkMatrix4x4()
    matrix.SetElement(1, 1, -1)
    logic.flip(self.volumeSelector.currentNode(), matrix)
  
  def onFlipZ(self):
    logic = INHSToolsLogic()
    matrix = vtk.vtkMatrix4x4()
    matrix.SetElement(2, 2, -1)
    logic.flip(self.volumeSelector.currentNode(), matrix)
  
  def INHSFile(self, filename):
    template = 'INHS'
    if(template in filename):
      return True
    else:
      return False
  
  def onImportVolume(self):
    logic = INHSToolsLogic()
    self.activeCellString = logic.getActiveCellByCol(15)
    currentSpecimenFileName = logic.getActiveCellByCol(12)
    self.currentSpecimenName, ext = os.path.splitext(currentSpecimenFileName)
    if bool(self.activeCellString):
      self.volumeNode = logic.runImportFromURL(self.activeCellString)
      if bool(self.volumeNode):
        self.launchMarkupsButton.enabled = True
        self.startSegmentationButton.enabled = True
        self.volumeSelector.setCurrentNode(self.volumeNode)
        self.activeRow = logic.getActiveCellRow()
        self.updateStatus(self.activeRow, 'Processing')
      else: 
        logging.debug("Error loading associated files.")
    else:
      logging.debug("No valid table cell selected.")
  
  def onExportLandmarks(self):
    if hasattr(self, 'fiducialNode'):
      fiducialName = os.path.splitext(self.activeCellString)[0]
      fiducialOutput = os.path.join(self.outputDirSelector.currentPath, fiducialName+'.fcsv')
      slicer.util.saveNode(self.fiducialNode, fiducialOutput)   
      self.updateTableAndGUI()         
      
  def updateTableAndGUI(self):
    self.updateStatus(self.activeRow, 'Complete')
    # clean up
    if hasattr(self, 'fiducialNode'):
      slicer.mrmlScene.RemoveNode(self.fiducialNode)  
    if hasattr(self, 'volumeNode'):
      slicer.mrmlScene.RemoveNode(self.volumeNode)
    if hasattr(self, 'segmentationNode'):
      slicer.mrmlScene.RemoveNode(self.segmentationNode)
    if hasattr(self, 'outputLabelmapNode'):
      slicer.mrmlScene.RemoveNode(self.outputLabelmapNode)
    self.selectorButton.enabled  = bool(self.tableSelector.currentPath)
    self.importVolumeButton.enabled = True
    self.flipXButton.enabled = False
    self.flipYButton.enabled = False
    self.flipZButton.enabled = False
    self.launchMarkupsButton.enabled = False
    self.exportLandmarksButton.enabled = False
    self.startSegmentationButton.enabled = False
    self.exportSegmentationButton.enabled = False
    #self.applySpacingButton.enabled = False
   
class LogDataObject:
  """This class i
     """
  def __init__(self):
    self.FileType = "NULL"
    self.X  = "NULL"
    self.Y = "NULL"
    self.Z = "NULL"
    self.Resolution = "NULL"
    self.Prefix = "NULL"
    self.SequenceStart = "NULL"
    self.SeqenceEnd = "NULL"
     
#
# INHSToolsLogic
#
class INHSToolsLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  def run(self, inputFile, spacingX, spacingY, spacingZ):
    """
    Run the actual algorithm
    """
    spacing = [spacingX, spacingY, spacingZ]
    inputFile.SetSpacing(spacing)
    
  def takeScreenshot(self,name,description,type=-1):
    # show the message even if not taking a screen shot
    slicer.util.delayDisplay('Take screenshot: '+description+'.\nResult is available in the Annotations module.', 3000)

    lm = slicer.app.layoutManager()
    # switch on the type to get the requested window
    widget = 0
    if type == slicer.qMRMLScreenShotDialog.FullLayout:
      # full layout
      widget = lm.viewport()
    elif type == slicer.qMRMLScreenShotDialog.ThreeD:
      # just the 3D window
      widget = lm.threeDWidget(0).threeDView()
    elif type == slicer.qMRMLScreenShotDialog.Red:
      # red slice window
      widget = lm.sliceWidget("Red")
    elif type == slicer.qMRMLScreenShotDialog.Yellow:
      # yellow slice window
      widget = lm.sliceWidget("Yellow")
    elif type == slicer.qMRMLScreenShotDialog.Green:
      # green slice window
      widget = lm.sliceWidget("Green")
    else:
      # default to using the full window
      widget = slicer.util.mainWindow()
      # reset the type so that the node is set correctly
      type = slicer.qMRMLScreenShotDialog.FullLayout

    # grab and convert to vtk image data
    qimage = ctk.ctkWidgetsUtils.grabWidget(widget)
    imageData = vtk.vtkImageData()
    slicer.qMRMLUtils().qImageToVtkImageData(qimage,imageData)

    annotationLogic = slicer.modules.annotations.logic()
    annotationLogic.CreateSnapShot(name, description, type, 1, imageData)
  
  def initializeSegmentation(self, masterVolumeNode):
    # Create segmentation
    segmentationName = masterVolumeNode.GetName()
    segmentationNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode', segmentationName +'_segmentation')
    segmentationNode.CreateDefaultDisplayNodes() # only needed for display
    segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(masterVolumeNode)
    segmentation = segmentationNode.GetSegmentation()
    # Add template segments
    self.addNewSegment(segmentation, "Dorsal Fin", (1.0, 1.0, 0.0))
    self.addNewSegment(segmentation, "Adipose Fin", (0.172549, 0.764706, 0.945098))
    self.addNewSegment(segmentation, "Caudal Fin", (0.396078, 0.027451, 0.447059))
    self.addNewSegment(segmentation, "Anal Fin", (0.513725, 0.764706, 0.180392))
    self.addNewSegment(segmentation, "Pelvic Fin", (1.0, 0.0, 0.0))
    self.addNewSegment(segmentation, "Pectoral Fin", (0.121569, 0.823529, 0.203922))
    self.addNewSegment(segmentation, "HeadEye", (0.0235294, 0.333333, 1.0))
    self.addNewSegment(segmentation, "Eye", (1.0, 0.0, 0.498039))
    self.addNewSegment(segmentation, "trunk", (1.0, 0.0, 1.0))
    self.addNewSegment(segmentation, "Caudal Fin Ray", (0.6392156862745098, 0.24705882352941178, 0.9607843137254902))
    self.addNewSegment(segmentation, "Alt Fin Ray", (0.9764705882352941, 0.5215686274509804, 0.19215686274509805))
    self.addNewSegment(segmentation, "Alt Fin Spine", (0.13725490196078433, 0.4588235294117647, 0.21568627450980393))
    return segmentationNode
    
  def addNewSegment(self,segmentation, name, color):
    segmentID = segmentation.AddEmptySegment(name)
    segmentation.GetSegment(segmentID).SetColor(color)
    
  def flip(self, volumeNode, transformMatrix):
    transform = slicer.vtkMRMLTransformNode()
    transform.SetName('FlipTransformation')
    slicer.mrmlScene.AddNode(transform)
    transform.SetMatrixTransformFromParent(transformMatrix)
    
    volumeNode.SetAndObserveTransformNodeID(transform.GetID())
    slicer.vtkSlicerTransformLogic().hardenTransform(volumeNode)
    slicer.mrmlScene.RemoveNode(transform)
    
  def getActiveCell(self):
    tableView=slicer.app.layoutManager().tableWidget(0).tableView()
    if bool(tableView.selectedIndexes()):
      index = tableView.selectedIndexes()[0]
      tableString = tableView.mrmlTableNode().GetCellText(index.row()-1,index.column())
      return tableString
    else:
      return ""
  
  def getActiveCellByCol(self, colNumber):
    tableView=slicer.app.layoutManager().tableWidget(0).tableView()
    if bool(tableView.selectedIndexes()):
      index = tableView.selectedIndexes()[0]
      tableString = tableView.mrmlTableNode().GetCellText(index.row()-1,colNumber)
      return tableString
    else:
      return ""
      
  def getActiveCellRow(self):
    tableView=slicer.app.layoutManager().tableWidget(0).tableView()
    if bool(tableView.selectedIndexes()):
      index = tableView.selectedIndexes()[0]
      return index.row()
    else:  
      return False
    
  def runImport(self,volumeFilename):
    volumePath = os.path.join(imagePathStr, volumeFilename)
    properties = {'singleFile': True}
    try:
      volumeNode = slicer.util.loadVolume(volumePath, properties)
      return volumeNode
    except:
      False
  
  def runImportFromURL(self,link):
    base = os.path.basename(link) 
    fileName = base.split('?')[0]
    fileNameBase, extension = os.path.splitext(fileName)
    if(extension in ['.dcm', '.nrrd', '.nii', '.mhd', '.mha', '.hdr', '.img', '.bmp', '.jpg', '.jpeg', '.png', '.tif', '.tiff']):
      fileTypes = 'VolumeFile'
    else:
      logging.debug('Could not download data. Not a supported file type.')   
      return False
      
    sampleDataLogic = SampleData.SampleDataLogic()
    loadedNodes = sampleDataLogic.downloadFromURL(
    nodeNames= fileNameBase,
    fileNames= fileName,
    loadFileTypes=fileTypes,
    loadFiles = True,
    uris= link)
    if(loadedNodes[0]):
      return loadedNodes[0]
    else:
      logging.debug('Load from URL failed')   
      return False
      
  def hideCompletedSamples(self, table):
    rowNumber = table.GetNumberOfRows()
    statusColumn = table.GetTable().GetColumnByName('Status')
    tableView=slicer.app.layoutManager().tableWidget(0).tableView()
    if not bool(statusColumn):
      return
    for currentRow in range(rowNumber):
      string = statusColumn.GetValue(currentRow)
      if (string): # any status should trigger hide row
        tableView.hideRow(currentRow+1)

    table.GetTable().Modified() # update table view
    
  def checkForStatusColumn(self, table, tableFilePath):
    columnNumber = table.GetNumberOfColumns()
    statusColumn = table.GetTable().GetColumnByName('Status')
    if not bool(statusColumn):
      print("Adding column for status")
      col1 = table.AddColumn()
      col1.SetName('User')
      col2 = table.AddColumn()
      col2.SetName('Status')
      table.GetTable().Modified() # update table view
      # Since no files have a status, write to file without reloading
      slicer.util.saveNode(table, tableFilePath)
     
class INHSToolsTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_INHSTools1()

  def test_INHSTools1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    import urllib
    downloads = (
        ('http://slicer.kitware.com/midas3/download?items=5767', 'FA.nrrd', slicer.util.loadVolume),
        )

    for url,name,loader in downloads:
      filePath = slicer.app.temporaryPath + '/' + name
      if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        logging.info('Requesting download %s from %s...\n' % (name, url))
        urllib.urlretrieve(url, filePath)
      if loader:
        logging.info('Loading %s...' % (name,))
        loader(filePath)
    self.delayDisplay('Finished with download and loading')

    volumeNode = slicer.util.getNode(pattern="FA")
    logic = INHSToolsLogic()
    self.assertIsNotNone( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')
