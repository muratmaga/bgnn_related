import SimpleITK as sitk
import sitkUtils
import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import numpy as np
import string
#
# INHSTools
#
#define global variable for node management
globalHardPath = 'C:/Users/Sara Rolfe/Downloads/fish' #collect nodes created by module
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
This module imports an image sequence from Bruker Skyscan microCT's into Slicer as a scalar 3D volume with correct image spacing. Accepted formats are TIF, PNG, JPG and BMP. 
User needs to be point out to the *_Rec.log file found in the reconstruction folder. 

This module was developed by Sara Rolfe and Murat Maga, through a NSF ABI Development grant, "An Integrated Platform for Retrieval, Visualization and Analysis of 
3D Morphology From Digital Biological Collections" (Award Numbers: 1759883).
https://nsf.gov/awardsearch/showAward?AWD_ID=1759883&HistoricalAwards=false 
""" # replace with organization, grant and thanks.

#
# INHSToolsWidget
#

class INHSToolsWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  def assignLayoutDescription(self, table):
    customLayout = """
    <layout type="horizontal" split="true">
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
    tableSelectorLable=qt.QLabel("Input table: ")
    self.tableSelector = ctk.ctkPathLineEdit()
    self.tableSelector.nameFilters=["*.csv"]
    self.tableSelector.setToolTip( "Select table with filenames to process" )
    #IOFormLayout.addRow("Input table: ", self.tableSelector)
    
    
    self.selectorButton = qt.QPushButton("Load Table")
    self.selectorButton.toolTip = "Load the table of image filenames to process"
    self.selectorButton.enabled = False
    #IOFormLayout.addRow(self.selectorButton)
    IOFormLayout.addWidget(tableSelectorLable,1,1)
    IOFormLayout.addWidget(self.tableSelector,1,2)
    IOFormLayout.addWidget(self.selectorButton,1,3)
    
    #
    # Import Button
    #
    self.importButton = qt.QPushButton("Import image")
    self.importButton.toolTip = "Import the image selected in the table"
    self.importButton.enabled = False
    #IOFormLayout.addRow(self.importButton)
    IOFormLayout.addWidget(self.importButton,2,1,1,3)
    
    #
    # Export Button
    #
    self.exportButton = qt.QPushButton("Export landmarks")
    self.exportButton.toolTip = "Export the landmarks  for the image selected in the table"
    self.exportButton.enabled = False
    #IOFormLayout.addRow(self.exportButton)
    IOFormLayout.addWidget(self.exportButton,3,1,1,3)
    
    #
    # Update table
    #
    self.updateTableButton = qt.QPushButton("Update table")
    self.updateTableButton.toolTip = "Save progress to CSV file and update the status column"
    self.updateTableButton.enabled = False
    #IOFormLayout.addRow(self.updateTableButton)
    IOFormLayout.addWidget(self.updateTableButton,4,1,1,3)
    
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
    # input spacing
    #
    spacingLayout= qt.QGridLayout()
    self.spacingX = ctk.ctkDoubleSpinBox()
    self.spacingX.value = 1
    self.spacingX.minimum = 0
    self.spacingX.singleStep = 1
    self.spacingX.setDecimals(2)
    self.spacingX.setToolTip("Input spacing X")
    
    self.spacingY = ctk.ctkDoubleSpinBox()
    self.spacingY.value = 1
    self.spacingY.minimum = 0
    self.spacingY.singleStep = 1
    self.spacingY.setDecimals(2)
    self.spacingY.setToolTip("Input spacing Y")
    
    self.spacingZ = ctk.ctkDoubleSpinBox()
    self.spacingZ.value = 1
    self.spacingZ.minimum = 0
    self.spacingZ.singleStep = 1
    self.spacingZ.setDecimals(2)
    self.spacingZ.setToolTip("Input spacing Z")
    
    spacingLayout.addWidget(self.spacingX,1,2)
    spacingLayout.addWidget(self.spacingY,1,3)
    spacingLayout.addWidget(self.spacingZ,1,4)
    
    parametersFormLayout.addRow("Spacing (mm):", spacingLayout)
    
    #
    # Apply Button
    #
    self.applySpacingButton = qt.QPushButton("Apply Spacing")
    self.applySpacingButton.toolTip = "Run the algorithm."
    self.applySpacingButton.enabled = False
    parametersFormLayout.addRow(self.applySpacingButton)
    
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
    
    # connections
    self.applySpacingButton.connect('clicked(bool)', self.onApplySpacingButton)
    self.flipXButton.connect('clicked(bool)', self.onFlipX)
    self.flipYButton.connect('clicked(bool)', self.onFlipY)
    self.flipZButton.connect('clicked(bool)', self.onFlipZ)
    self.selectorButton.connect('clicked(bool)', self.onLoadTable)
    self.volumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.tableSelector.connect("validInputChanged(bool)", self.onSelectTablePath)
    self.importButton.connect('clicked(bool)', self.onImport)
    self.exportButton.connect('clicked(bool)', self.onExport)
    self.updateTableButton.connect('clicked(bool)', self.onUpdateTable)

    # Add vertical spacer
    self.layout.addStretch(1)

    # Refresh Apply button state
    self.onSelect()
    
  def cleanup(self):
    pass
  
  def updateStatus(self, index, string):
    # refresh table from file, update the status column, and save 
    name = self.fileTable.GetName()
    slicer.mrmlScene.RemoveNode(self.fileTable)
    self.fileTable = slicer.util.loadNodeFromFile(self.tableSelector.currentPath, 'TableFile')
    self.fileTable.SetName(name)
    statusColumn = self.fileTable.GetTable().GetColumnByName('Status')
    statusColumn.SetValue(index-1, string)
    self.fileTable.GetTable().Modified() # update table view
    slicer.util.saveNode(self.fileTable, self.tableSelector.currentPath)
    
  def onSelectTablePath(self):
    if(self.tableSelector.currentPath):
      self.selectorButton.enabled = True
    else:
      self.selectorButton.enabled  = False
  
  def onLoadTable(self):
    print("loading file")
    self.fileTable = slicer.util.loadNodeFromFile(self.tableSelector.currentPath, 'TableFile')
    if bool(self.fileTable):
      logic = INHSToolsLogic()
      logic.checkForStatusColumn(self.fileTable, self.tableSelector.currentPath) # if not present adds and saves to file
      self.importButton.enabled = True
      self.assignLayoutDescription(self.fileTable)
    else:
      self.importButton.enabled = False
  
  def onSelect(self):
    if bool(self.volumeSelector.currentNode()):  
      if self.INHSFile(self.volumeSelector.currentNode().GetName()):
        self.applySpacingButton.enabled =True
        self.flipXButton.enabled = True
        self.flipYButton.enabled = True
        self.flipZButton.enabled = True
      else:
        print("File name must include string: 'INHS'")
        logging.debug("Invalid filename: must include string: 'INHS'")
        self.applySpacingButton.enabled = False
        self.flipXButton.enabled = False
        self.flipYButton.enabled = False
        self.flipZButton.enabled = False
    else:
      self.applySpacingButton.enabled = False
      self.flipXButton.enabled = False
      self.flipYButton.enabled = False
      self.flipZButton.enabled = False  

  def onApplySpacingButton(self):
    logic = INHSToolsLogic()
    logic.run(self.volumeSelector.currentNode(), self.spacingX.value, self.spacingY.value, self.spacingZ.value)
  
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
  
  def onImport(self):
    logic = INHSToolsLogic()
    activeCellString = logic.getActiveCell()
    if bool(activeCellString):
      if self.INHSFile(activeCellString):
        self.volumeNode = logic.runImport(activeCellString)
        if bool(self.volumeNode):
          name = self.volumeNode.GetName()
          self.fiducialNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode",name)
          self.exportButton.enabled = True  
          self.volumeSelector.setCurrentNode(self.volumeNode)
          self.activeRow = logic.getActiveCellRow()
          self.updateStatus(self.activeRow, 'Processing')
        else: 
          logging.debug("Error loading associated files.")
      else:
        logging.debug("Invalid filename: must include string: 'INHS'")
    else:
      logging.debug("No valid table cell selected.")
  
  def onExport(self):
    if bool(self.fiducialNode):
      fiducialName = self.fiducialNode.GetName()
      fiducialOutput = os.path.join(globalHardPath, fiducialName+'.fcsv')
      slicer.util.saveNode(self.fiducialNode, fiducialOutput)   
      self.updateTableButton.enabled = True      
      
  def onUpdateTable(self):
    self.updateStatus(self.activeRow, 'Complete')
    if bool(self.fiducialNode):  
      slicer.mrmlScene.RemoveNode(self.fiducialNode)  
    if bool(self.volumeNode):
      slicer.mrmlScene.RemoveNode(self.volumeNode)
    self.exportButton.enabled = False 
    self.importButton.enabled = False 
    self.selectorButton.enabled  = False
    self.applySpacingButton.enabled = False
    self.flipXButton.enabled = False
    self.flipYButton.enabled = False
    self.flipZButton.enabled = False 
    self.updateTableButton.enabled = False
    self.tableSelector.setCurrentPath('')
    
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
      indexTuple = [index.row(), index.column()]
      tableString = tableView.mrmlTableNode().GetCellText(index.row()-1,index.column())
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
    volumePath = os.path.join(globalHardPath, volumeFilename)
    properties = {'singleFile': True}
    try:
      volumeNode = slicer.util.loadVolume(volumePath, properties)
      return volumeNode
    except:
      False
  
  def checkForStatusColumn(self, table, tableFilePath):
    columnNumber = table.GetNumberOfColumns()
    lastColumnName = table.GetColumnName(columnNumber-1)
    if bool(lastColumnName != 'Status'):
      print(lastColumnName, ' not Status')
      print("Adding column for status")
      col = table.AddColumn()
      col.SetName('Status')
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
