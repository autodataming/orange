"""
<name>Linear Projection</name>
<description>Create a linear projection.</description>
<contact>Gregor Leban (gregor.leban@fri.uni-lj.si)</contact>
<icon>icons/LinearProjection.png</icon>
<priority>2000</priority>
"""
# LinProj.py
#
# Show a linear projection of the data
#

from OWVisWidget import *
from OWLinProjGraph import *
from OWkNNOptimization import OWVizRank
##from OWClusterOptimization import *
from OWFreeVizOptimization import *
import OWToolbars, OWGUI, orngTest
import orngVisFuncts, OWDlgs
import orngVizRank

###########################################################################################
##### WIDGET : Linear Projection
###########################################################################################
class OWLinProj(OWVisWidget):
    settingsList = ["graph.pointWidth", "graph.jitterSize", "graph.globalValueScaling", "graph.showFilledSymbols", "graph.scaleFactor",
                    "graph.showLegend", "graph.useDifferentSymbols", "autoSendSelection", "graph.useDifferentColors", "graph.showValueLines",
                    "graph.tooltipKind", "graph.tooltipValue", "toolbarSelection",
                    "showProbabilitiesDetails", "graph.showProbabilities", "graph.squareGranularity", "graph.spaceBetweenCells",
                    "valueScalingType", "showAllAttributes", "colorSettings", "selectedSchemaIndex", "addProjectedPositions"]
    jitterSizeNums = [0.0, 0.01, 0.1, 0.5, 1, 2, 3, 4, 5, 7, 10, 15, 20]
    jitterSizeList = [str(x) for x in jitterSizeNums]

    contextHandlers = {"": DomainContextHandler("", [ContextField("shownAttributes", DomainContextHandler.RequiredList, selected="selectedShown", reservoir="hiddenAttributes")])}

    def __init__(self,parent=None, signalManager = None, name = "Linear Projection", graphClass = None):
        OWVisWidget.__init__(self, parent, signalManager, name, TRUE)

        self.inputs = [("Examples", ExampleTable, self.setData, Default), ("Example Subset", ExampleTable, self.setSubsetData), ("Attribute Selection List", AttributeList, self.setShownAttributes), ("Evaluation Results", orngTest.ExperimentResults, self.setTestResults), ("VizRank Learner", orange.Learner, self.setVizRankLearner)]
        self.outputs = [("Selected Examples", ExampleTable), ("Unselected Examples", ExampleTable), ("Attribute Selection List", AttributeList), ("FreeViz Learner", orange.Learner)]

        # local variables
        self.showAllAttributes = 0
        self.valueScalingType = 0
        self.autoSendSelection = 1
        self.data = None
        self.unprocessedSubsetData = None
        self.toolbarSelection = 0
        self.classificationResults = None
        self.outlierValues = None
        self.attributeSelectionList = None
        self.colorSettings = None
        self.selectedSchemaIndex = 0
        self.addProjectedPositions = 0
        self.resetAnchors = 0

        self.showProbabilitiesDetails = 0
        self.boxGeneral = 1

        #add a graph widget
        self.box = QVBoxLayout(self.mainArea)
        if graphClass:
            self.graph = graphClass(self, self.mainArea, name)
        else:
            self.graph = OWLinProjGraph(self, self.mainArea, name)
        self.box.addWidget(self.graph)

        # graph variables
        self.graph.manualPositioning = 0
        self.graph.hideRadius = 0
##        self.graph.showClusters = 0
        self.graph.showAnchors = 1
        self.graph.jitterContinuous = 0
        self.graph.showProbabilities = 0
        self.graph.useDifferentSymbols = 0
        self.graph.useDifferentColors = 1
        self.graph.tooltipKind = 0
        self.graph.tooltipValue = 0
        self.graph.scaleFactor = 1.0
        self.graph.squareGranularity = 3
        self.graph.spaceBetweenCells = 1
        self.graph.showAxisScale = 0
        self.graph.showValueLines = 0
        self.graph.valueLineLength = 5

        #load settings
        self.loadSettings()

##        # cluster dialog
##        self.clusterDlg = ClusterOptimization(self, self.signalManager, self.graph, name)
##        self.graph.clusterOptimization = self.clusterDlg

        # optimization dialog
        if name.lower() == "radviz":
            self.vizrank = OWVizRank(self, self.signalManager, self.graph, orngVizRank.RADVIZ, name)
            self.connect(self.graphButton, SIGNAL("clicked()"), self.saveToFile)
        elif name.lower() == "polyviz":
            self.vizrank = OWVizRank(self, self.signalManager, self.graph, orngVizRank.POLYVIZ, name)
            self.connect(self.graphButton, SIGNAL("clicked()"), self.graph.saveToFile)
        else:
            self.vizrank = OWVizRank(self, self.signalManager, self.graph, orngVizRank.LINEAR_PROJECTION, name)
            self.connect(self.graphButton, SIGNAL("clicked()"), self.saveToFile)

        self.optimizationDlg = self.vizrank  # for backward compatibility

        self.graph.normalizeExamples = (name.lower() == "radviz")       # ignore settings!! if we have radviz then normalize, otherwise not.

        #GUI
        # add a settings dialog and initialize its values
        self.tabs = QTabWidget(self.space, 'tabWidget')
        self.GeneralTab = QVGroupBox(self)
        #self.GeneralTab.setFrameShape(QFrame.NoFrame)
        self.SettingsTab = QVGroupBox(self)
        self.tabs.insertTab(self.GeneralTab, "Main")
        self.tabs.insertTab(self.SettingsTab, "Settings")

        #add controls to self.controlArea widget
        self.createShowHiddenLists(self.GeneralTab, callback = self.updateGraphAndAnchors)

        self.optimizationButtons = OWGUI.widgetBox(self.GeneralTab, "Optimization Dialogs", orientation = "horizontal")
        self.vizrankButton = OWGUI.button(self.optimizationButtons, self, "VizRank", callback = self.vizrank.reshow, tooltip = "Opens VizRank dialog where you can search for interesting projections with different subsets of attributes.", debuggingEnabled = 0)
        self.wdChildDialogs = [self.vizrank]    # used when running widget debugging

        # freeviz dialog
        if name.lower() in ["linear projection", "radviz"]:
            self.freeVizDlg = FreeVizOptimization(self, self.signalManager, self.graph, name)
            self.wdChildDialogs.append(self.freeVizDlg)
            self.freeVizDlgButton = OWGUI.button(self.optimizationButtons, self, "FreeViz", callback = self.freeVizDlg.reshow, tooltip = "Opens FreeViz dialog, where the position of attribute anchors is optimized so that class separation is improved", debuggingEnabled = 0)
            if name.lower() == "linear projection":
                self.freeVizLearner = FreeVizLearner(self.freeVizDlg)
                self.send("FreeViz Learner", self.freeVizLearner)
                
##        self.clusterDetectionDlgButton = OWGUI.button(self.optimizationButtons, self, "Cluster", callback = self.clusterDlg.reshow, debuggingEnabled = 0)
##        self.vizrankButton.setMaximumWidth(63)
##        self.clusterDetectionDlgButton.setMaximumWidth(63)
##        self.freeVizDlgButton.setMaximumWidth(63)
##        self.connect(self.clusterDlg.startOptimizationButton , SIGNAL("clicked()"), self.optimizeClusters)
##        self.connect(self.clusterDlg.resultList, SIGNAL("selectionChanged()"),self.showSelectedCluster)

        self.zoomSelectToolbar = OWToolbars.ZoomSelectToolbar(self, self.GeneralTab, self.graph, self.autoSendSelection)
        self.graph.selectionChangedCallback = self.selectionChanged
        self.connect(self.zoomSelectToolbar.buttonSendSelections, SIGNAL("clicked()"), self.sendSelections)

        # ####################################
        # SETTINGS TAB
        # #####
        self.extraTopBox = OWGUI.widgetBox(self.SettingsTab, orientation = "vertical")
        self.extraTopBox.hide()
        OWGUI.hSlider(self.SettingsTab, self, 'graph.pointWidth', box='Point size', minValue=1, maxValue=15, step=1, callback = self.updateGraph)

        box = OWGUI.widgetBox(self.SettingsTab, "Jittering Options")
        box2 = OWGUI.widgetBox(self.SettingsTab, "Scaling Options")
        box3 = OWGUI.collapsableWidgetBox(self.SettingsTab, "General Graph Settings", self, "boxGeneral")
        box8 = OWGUI.widgetBox(self.SettingsTab, "Colors", orientation = "horizontal")
        box9 = OWGUI.widgetBox(self.SettingsTab, "Tooltips Settings")
        box10 = OWGUI.widgetBox(self.SettingsTab, "Sending Selection")

        OWGUI.comboBox(box9, self, "graph.tooltipKind", items = ["Show line tooltips", "Show visible attributes", "Show all attributes"], callback = self.updateGraph)
        OWGUI.comboBox(box9, self, "graph.tooltipValue", items = ["Tooltips show data values", "Tooltips show spring values"], callback = self.updateGraph, tooltip = "Do you wish that tooltips would show you original values of visualized attributes or the 'spring' values (values between 0 and 1). \nSpring values are scaled values that are used for determining the position of shown points. Observing these values will therefore enable you to \nunderstand why the points are placed where they are.")

        OWGUI.checkBox(box10, self, 'autoSendSelection', 'Auto send selected/unselected data', callback = self.selectionChanged, tooltip = "Send signals with selected data whenever the selection changes.")
        OWGUI.comboBox(box10, self, "addProjectedPositions", items = ["Do not modify the domain", "Append projection as attributes", "Append projection as meta attributes"], callback = self.sendSelections)
        self.selectionChanged()

        # this is needed so that the tabs are wide enough!
        self.safeProcessEvents()
        self.tabs.updateGeometry()

        OWGUI.comboBoxWithCaption(box, self, "graph.jitterSize", 'Jittering size (% of range):  ', callback = self.resetGraphData, items = self.jitterSizeNums, sendSelectedValue = 1, valueType = float)
        OWGUI.checkBox(box, self, 'graph.jitterContinuous', 'Jitter continuous attributes', callback = self.resetGraphData, tooltip = "Does jittering apply also on continuous attributes?")

        OWGUI.qwtHSlider(box2, self, "graph.scaleFactor", minValue=1.0, maxValue= 10.0, step=0.1, label ='Inflate points by:'+'     ', callback = self.updateGraph, tooltip="If points lie too much together you can expand their position to improve perception")
        valueScalingList = ["attribute range", "global range", "attribute variance"]
        if name.lower() in ["radviz", "polyviz"]:
            valueScalingList.pop(); self.valueScalingType = min(self.valueScalingType, 1)
        OWGUI.comboBoxWithCaption(box2, self, "valueScalingType", 'Scale values by: ', callback = self.setValueScaling, items = valueScalingList)

        #OWGUI.checkBox(box3, self, 'graph.normalizeExamples', 'Normalize examples', callback = self.updateGraph)
        OWGUI.checkBox(box3, self, 'graph.showLegend', 'Show legend', callback = self.updateGraph)
        box33 = OWGUI.widgetBox(box3, orientation = "horizontal")
        OWGUI.checkBox(box33, self, 'graph.showValueLines', 'Show value lines', callback = self.updateGraph)
        OWGUI.hSlider(box33, self, 'graph.valueLineLength', minValue=1, maxValue=10, step=1, callback = self.updateGraph, createLabel = 0)
        OWGUI.checkBox(box3, self, 'graph.useDifferentSymbols', 'Use different symbols', callback = self.updateGraph, tooltip = "Show different class values using different symbols")
        OWGUI.checkBox(box3, self, 'graph.useDifferentColors', 'Use different colors', callback = self.updateGraph, tooltip = "Show different class values using different colors")
        OWGUI.checkBox(box3, self, 'graph.showFilledSymbols', 'Show filled symbols', callback = self.updateGraph)
##        OWGUI.checkBox(box3, self, 'graph.showClusters', 'Show clusters', callback = self.updateGraph, tooltip = "Show a line boundary around a significant cluster")

        box5 = OWGUI.widgetBox(box3, orientation = "horizontal")
        box6 = OWGUI.widgetBox(box3, orientation = "horizontal")
        box7 = OWGUI.widgetBox(box3, orientation = "horizontal")

        OWGUI.checkBox(box5, self, 'graph.showProbabilities', 'Show probabilities'+'  ', callback = self.updateGraph, tooltip = "Show a background image with class probabilities")
        hider = OWGUI.widgetHider(box5, self, "showProbabilitiesDetails", tooltip = "Show/hide extra settings")
        rubb = OWGUI.rubber(box5)
        rubb.setSizePolicy(QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Maximum))

        OWGUI.separator(box6, width=20)
        OWGUI.label(box6, self, "Granularity:"+"  ")
        OWGUI.hSlider(box6, self, 'graph.squareGranularity', minValue=1, maxValue=10, step=1, callback = self.updateGraph)

        OWGUI.separator(box7, width=20)
        OWGUI.checkBox(box7, self, 'graph.spaceBetweenCells', 'Show space between cells', callback = self.updateGraph)
        hider.setWidgets([box6, box7])

        OWGUI.button(box8, self, "Colors", self.setColors, tooltip = "Set the canvas background color and color palette for coloring continuous variables", debuggingEnabled = 0)

        self.icons = self.createAttributeIconDict()
        self.debugSettings = ["hiddenAttributes", "shownAttributes"]

        # add a settings dialog and initialize its values
        self.activateLoadedSettings()
        self.setValueScaling() # XXX is there any better way to do this?!
        self.resize(900, 700)


    def saveToFile(self):
        self.graph.saveToFile([("Save PicTex", self.graph.savePicTeX)])

    def activateLoadedSettings(self):
        dlg = self.createColorDialog()
        self.graph.contPalette = dlg.getContinuousPalette("contPalette")
        self.graph.discPalette = dlg.getDiscretePalette()
        self.graph.setCanvasBackground(dlg.getColor("Canvas"))

        apply([self.zoomSelectToolbar.actionZooming, self.zoomSelectToolbar.actionRectangleSelection, self.zoomSelectToolbar.actionPolygonSelection][self.toolbarSelection], [])

        self.cbShowAllAttributes()
        self.setValueScaling()


    # #########################
    # KNN OPTIMIZATION BUTTON EVENTS
    # #########################
    def saveCurrentProjection(self):
        qname = QFileDialog.getSaveFileName( os.path.realpath(".") + "/Linear_projection.tab", "Orange Example Table (*.tab)", self, "", "Save File")
        if qname.isEmpty(): return
        name = str(qname)
        if len(name) < 4 or name[-4] != ".":
            name = name + ".tab"
        self.graph.saveProjectionAsTabData(name, self.getShownAttributeList())


##    # ################################################################################################
##    # find projections that have tight clusters of points that belong to the same class value
##    def optimizeClusters(self):
##        if self.data == None: return
##        if not self.hasDiscreteClass(self.data):
##            QMessageBox.critical( None, "Cluster Detection Dialog", 'Clusters can be detected only in data sets with a discrete class value', QMessageBox.Ok)
##            return
##
##        self.clusterDlg.clearResults()
##        self.clusterDlg.clusterStabilityButton.setOn(0)
##        self.clusterDlg.pointStability = None
##
##        try:
##            listOfAttributes = self.vizrank.getEvaluatedAttributes(self.data)
##            text = str(self.vizrank.attributeCountCombo.currentText())
##            if text == "ALL": maxLen = len(listOfAttributes)
##            else:             maxLen = int(text)
##
##            if self.clusterDlg.getOptimizationType() == self.clusterDlg.EXACT_NUMBER_OF_ATTRS: minLen = maxLen
##            else: minLen = 3
##
##            possibilities = 0
##            for i in range(minLen, maxLen+1): possibilities += orngVisFuncts.combinationsCount(i, len(listOfAttributes))* orngVisFuncts.fact(i-1)/2
##
##            self.graph.totalPossibilities = possibilities
##            self.graph.triedPossibilities = 0
##
##            if self.graph.totalPossibilities > 20000:
##                proj = str(self.graph.totalPossibilities)
##                l = len(proj)
##                for i in range(len(proj)-2, 0, -1):
##                    if (l-i)%3 == 0: proj = proj[:i] + "," + proj[i:]
##                self.printEvent("OWLinProj: Warning: There are %s possible projections using currently visualized attributes"% (proj), eventVerbosity = 1)
##
##            self.clusterDlg.disableControls()
##
##            self.graph.getOptimalClusters(listOfAttributes, minLen, maxLen, self.clusterDlg.addResult)
##        except:
##            type, val, traceback = sys.exc_info()
##            sys.excepthook(type, val, traceback)  # print the exception
##
##        self.clusterDlg.enableControls()
##        self.clusterDlg.finishedAddingResults()
##        self.showSelectedCluster()


    # send signals with selected and unselected examples as two datasets
    def sendSelections(self):
        if not self.data: return
        (selected, unselected) = self.graph.getSelectionsAsExampleTables(self.getShownAttributeList(), addProjectedPositions = self.addProjectedPositions)

        self.send("Selected Examples",selected)
        self.send("Unselected Examples",unselected)

    def sendShownAttributes(self):
        self.send("Attribute Selection List", [a[0] for a in self.shownAttributes])


    # show selected interesting projection
    def showSelectedAttributes(self):
        val = self.vizrank.getSelectedProjection()
        if val:
            (accuracy, other_results, tableLen, attrList, tryIndex, generalDict) = val
            self.updateGraph(attrList, setAnchors= 1, XAnchors = generalDict.get("XAnchors"), YAnchors = generalDict.get("YAnchors"))
            self.graph.removeAllSelections()


##    def showSelectedCluster(self):
##        val = self.clusterDlg.getSelectedCluster()
##        if not val: return
##        (value, closure, vertices, attrList, classValue, enlargedClosure, other, strList) = val
##
##        if self.clusterDlg.clusterStabilityButton.isOn():
##            validData = self.graph.getValidList([self.graph.attributeNames.index(attr) for attr in attrList])
##            insideColors = (numpy.compress(validData, self.clusterDlg.pointStability), "Point inside a cluster in %.2f%%")
##        else: insideColors = None
##
##        self.updateGraph(attrList, 1, insideColors, clusterClosure = (closure, enlargedClosure, classValue))
##        self.graph.removeAllSelections()


    def updateGraphAndAnchors(self):
        self.updateGraph(setAnchors = 1)

    def updateGraph(self, attrList = None, setAnchors = 0, insideColors = None, clusterClosure = None, **args):
        if not attrList:
            attrList = self.getShownAttributeList()
        else:
            self.setShownAttributeList(self.data, attrList)

        self.graph.showKNN = 0
        if self.hasDiscreteClass(self.data):
            self.graph.showKNN = self.vizrank.showKNNCorrectButton.isOn() and 1 or  self.vizrank.showKNNCorrectButton.isOn() and 2

        self.graph.insideColors = insideColors or self.classificationResults or self.outlierValues
##        self.graph.clusterClosure = clusterClosure

        self.graph.updateData(attrList, setAnchors, **args)
        self.graph.repaint()


    # ###############################################################################################################
    # INPUT SIGNALS

    # receive new data and update all fields
    def setData(self, data):
        if data:
            name = getattr(data, "name", "")
            data = data.filterref(orange.Filter_hasClassValue())
            data.name = name
            if len(data) == 0 or len(data.domain) == 0:        # if we don't have any examples or attributes then this is not a valid data set
                data = None
        if self.data and data and self.data.checksum() == data.checksum():
            return    # check if the new data set is the same as the old one

        self.closeContext()
        exData = self.data
        self.data = data
        self.vizrank.setData(data)
##        self.clusterDlg.setData(data)
        if hasattr(self, "freeVizDlg"):
            self.freeVizDlg.setData(data)
        self.classificationResults = None
        self.outlierValues = None

        sameDomain = self.data and exData and exData.domain.checksum() == self.data.domain.checksum() # preserve attribute choice if the domain is the same
        if not sameDomain:
            self.setShownAttributeList(self.data, self.attributeSelectionList)
        self.resetAnchors += not sameDomain

        self.openContext("", data)
        self.resetAttrManipulation()

        if data and self.unprocessedSubsetData:        # if we first received subset data we now have to call setSubsetData to process it
            self.setSubsetData(self.unprocessedSubsetData)
            self.unprocessedSubsetData = None


    def setSubsetData(self, data, update = 1):
        if not self.data:
            self.unprocessedSubsetData = data
            self.warning(10)
            return

        if self.graph.rawSubsetData != None and data != None and self.graph.rawSubsetData.checksum() == data.checksum():
            return    # check if the new data set is the same as the old one

        try:
            subsetData = data.select(self.data.domain)
            self.warning(10)
        except:
            subsetData = None
            self.warning(10, data and "'Examples' and 'Example Subset' data do not have copatible domains. Unable to draw 'Example Subset' data." or "")

        self.vizrank.setSubsetData(subsetData)
#        if update: self.updateGraph()
##        self.clusterDlg.setSubsetData(data)
#        qApp.processEvents()


    # attribute selection signal - info about which attributes to show
    def setShownAttributes(self, attributeSelectionList):
        self.attributeSelectionList = attributeSelectionList
        if self.data and self.attributeSelectionList:
            for attr in self.attributeSelectionList:
                if not self.graph.attributeNameIndex.has_key(attr):  # this attribute list belongs to a new dataset that has not come yet
                    return

            self.setShownAttributeList(self.data, self.attributeSelectionList)
            self.attributeSelectionList = None
            self.selectionChanged()
        self.resetAnchors += 1

    # visualize the results of the classification
    def setTestResults(self, results):
        self.classificationResults = None
        if isinstance(results, orngTest.ExperimentResults) and len(results.results) > 0 and len(results.results[0].probabilities) > 0:
            self.classificationResults = ([results.results[i].probabilities[0][results.results[i].actualClass] for i in range(len(results.results))], "Probability of correct classificatioin = %.2f%%")
        self.resetAnchors += 1


    # set the learning method to be used in VizRank
    def setVizRankLearner(self, learner):
        self.vizrank.externalLearner = learner

    # this is called by OWBaseWidget after setData and setSubsetData are called. this way the graph is updated only once
    def handleNewSignals(self):
        self.updateGraph(setAnchors = self.resetAnchors)
        self.sendSelections()
        self.resetAnchors = 0

    # EVENTS
    def resetBmpUpdateValues(self):
        self.graph.potentialsBmp = None
        self.updateGraph()

    def resetGraphData(self):
        orngScaleLinProjData.setData(self.graph, self.data)
        #self.graph.setData(self.data)
        self.updateGraph()

    def setValueScaling(self):
        self.graph.insideColors = self.graph.clusterClosure = None
        if self.valueScalingType == 0:
            self.graph.globalValueScaling = self.graph.scalingByVariance = 0
        elif self.valueScalingType == 1:
            self.graph.globalValueScaling = 1
            self.graph.scalingByVariance = 0
        else:
            self.graph.globalValueScaling = 0
            self.graph.scalingByVariance = 1
        #self.graph.setData(self.data)
        orngScaleLinProjData.setData(self.graph, self.data)
        self.graph.potentialsBmp = None
        self.updateGraph()


    def selectionChanged(self):
        self.zoomSelectToolbar.buttonSendSelections.setEnabled(not self.autoSendSelection)
        if self.autoSendSelection:
            self.sendSelections()

    def setColors(self):
        dlg = self.createColorDialog()
        if dlg.exec_loop():
            self.colorSettings = dlg.getColorSchemas()
            self.selectedSchemaIndex = dlg.selectedSchemaIndex
            self.graph.contPalette = dlg.getContinuousPalette("contPalette")
            self.graph.discPalette = dlg.getDiscretePalette()
            self.graph.setCanvasBackground(dlg.getColor("Canvas"))
            self.updateGraph()

    def createColorDialog(self):
        c = OWDlgs.ColorPalette(self, "Color palette")
        c.createDiscretePalette("Discrete palette")
        c.createContinuousPalette("contPalette", "Continuous palette")
        box = c.createBox("otherColors", "Other colors")
        c.createColorButton(box, "Canvas", "Canvas color", Qt.white)
        c.setColorSchemas(self.colorSettings, self.selectedSchemaIndex)
        box.addSpace(5)
        box.adjustSize()
        return c

    def saveSettings(self):
        OWWidget.saveSettings(self)
        self.vizrank.saveSettings()
        if hasattr(self, "freeVizDlg"):
            self.freeVizDlg.saveSettings()

    def destroy(self, dw = 1, dsw = 1):
##        self.clusterDlg.hide()
        self.vizrank.hide()
        if hasattr(self, "freeVizDlg"):
            self.freeVizDlg.hide()
        OWVisWidget.destroy(self, dw, dsw)


#test widget appearance
if __name__=="__main__":
    a=QApplication(sys.argv)
    ow=OWLinProj()
    a.setMainWidget(ow)
    ow.show()
    ow.setData(orange.ExampleTable("..\\..\\doc\\datasets\\zoo.tab"))
    a.exec_loop()

    #save settings
    ow.saveSettings()
