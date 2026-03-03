# encoding: utf-8
from __future__ import division, print_function, unicode_literals

#######################################################################################
#
# Reporter Plugin
#
# Read the docs:
# https://github.com/schriftgestalt/GlyphsSDK/tree/master/Python%20Templates/Reporter
#
#######################################################################################

import objc
from GlyphsApp import Glyphs
from GlyphsApp.plugins import ReporterPlugin
from math import radians, tan
from Cocoa import NSBezierPath, NSColor, NSFont, NSAttributedString, NSMakeRect, NSPoint, NSFontAttributeName, NSForegroundColorAttributeName


class ShowCrosshairOnSelect(ReporterPlugin):

	@objc.python_method
	def settings(self):
		self.menuName = Glyphs.localize({
			'en': u'Crosshair On Select',
		})

		# Glyphs.registerDefault("com.wwwhhhhh.ShowCrosshairOnSelect.universalCrosshair", 1)
		Glyphs.registerDefault("com.wwwhhhhh.ShowCrosshairOnSelect.showCoordinates", 0)
		Glyphs.registerDefault("com.wwwhhhhh.ShowCrosshairOnSelect.showThickness", 0)
		Glyphs.registerDefault("com.wwwhhhhh.ShowCrosshairOnSelect.fontSize", 10.0)
		Glyphs.registerDefault("com.wwwhhhhh.ShowCrosshairOnSelect.ignoreItalicAngle", 0)

		self.generalContextMenus = self.buildContextMenus()

	@objc.python_method
	def buildContextMenus(self, sender=None):
		return [
			{
				'name': Glyphs.localize({
					'en': "Crosshair On Select Options:",
				}),
				'action': None,
			},
			# {
			# 	'name': Glyphs.localize({
			# 		'en': "Always Show Crosshair",
			# 		}),
			# 	'action': self.toggleUniversalCrosshair,
			# 	'state': Glyphs.defaults["com.wwwhhhhh.ShowCrosshairOnSelect.universalCrosshair"],
			# },
			{
				'name': Glyphs.localize({
					'en': "Show Coordinates",
				}),
				'action': self.toggleShowCoordinates,
				'state': Glyphs.defaults["com.wwwhhhhh.ShowCrosshairOnSelect.showCoordinates"],
			},
			{
				'name': Glyphs.localize({
					'en': "Show Thicknesses",
				}),
				'action': self.toggleShowThickness,
				'state': Glyphs.defaults["com.wwwhhhhh.ShowCrosshairOnSelect.showThickness"],
			},
		]

	@objc.python_method
	def drawCircle(self, center, size):
		radius = size * 0.5
		circle = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
			NSMakeRect(center.x - radius, center.y - radius, size, size),
			radius,
			radius,
		)
		circle.fill()

	@objc.python_method
	def drawThickness(self, layer, selectionPosition):

		if layer is None:
			return
		font = layer.font()
		master = layer.associatedFontMaster()
		scale = self.getScale()

		# intersection markers:
		handleSize = self.getHandleSize()
		try:
			NSColor.separatorColor().set()
		except:
			NSColor.systemGrayColor().set()  # pre 10.14

		# stem thickness horizontal slice
		sliceY = selectionPosition.y
		minX = -1000 * (font.upm / 1000.0)
		maxX = layer.width + 1000 * (font.upm / 1000.0)
		prev = minX
		xs = {}
		intersections = layer.calculateIntersectionsStartPoint_endPoint_decompose_(
			(minX, sliceY),
			(maxX, sliceY),
			True,
		)
		for inter in intersections[1:-1]:
			self.drawCircle(inter, handleSize)
			if prev != minX:
				xs[(inter.x - prev) / 2 + prev] = inter.x - prev
			prev = inter.x

		# stem thickness vertical slice
		sliceX = selectionPosition.x
		minY = master.descender - 1000 * (font.upm / 1000.0)
		maxY = master.ascender + 1000 * (font.upm / 1000.0)
		prev = minY
		ys = {}

		italicAngle = master.italicAngle

		verticalIntersections = layer.calculateIntersectionsStartPoint_endPoint_decompose_(
			self.italicize(NSPoint(sliceX, minY), italicAngle=italicAngle, pivotalY=sliceY),
			self.italicize(NSPoint(sliceX, maxY), italicAngle=italicAngle, pivotalY=sliceY),
			True,
		)
		for inter in verticalIntersections[1:-1]:
			self.drawCircle(inter, handleSize)
			if prev != minY:
				ys[(inter.y - prev) / 2 + prev] = inter.y - prev
			prev = inter.y

		# set font attributes
		fontSize = Glyphs.defaults["com.wwwhhhhh.ShowCrosshairOnSelect.fontSize"]
		thicknessFontAttributes = {
			NSFontAttributeName: NSFont.monospacedDigitSystemFontOfSize_weight_(fontSize, 0.0),
			NSForegroundColorAttributeName: NSColor.textColor()
		}

		layerOrigin = self.controller.selectedLayerOrigin
		print("__layerOrigin", layerOrigin)
		# number badges on vertical slice:
		for key in ys:
			item = ys[key]
			item = round(item, 1)
			if item != 0:
				x, y = sliceX, key
				x *= scale
				y *= scale
				x += layerOrigin.x
				y += layerOrigin.y
				# adjust x for italic angle if necessary:
				if italicAngle:
					x = self.italicize(NSPoint(x, y), italicAngle=italicAngle, pivotalY=sliceY).x
				self.drawThicknessBadge(fontSize, x, y, item)
				self.drawThicknessText(thicknessFontAttributes, x, y, item)

		# number badges on horizontal slice:
		for key in xs:
			item = xs[key]
			item = round(item, 1)
			if item != 0:
				x, y = key, sliceY
				x *= scale
				y *= scale
				x += layerOrigin.x
				y += layerOrigin.y
				self.drawThicknessBadge(fontSize, x, y, item)
				self.drawThicknessText(thicknessFontAttributes, x, y, item)

	@objc.python_method
	def italicize(self, thisPoint, italicAngle=0.0, pivotalY=0.0):
		"""
		Returns the italicized position of an NSPoint 'thisPoint'
		for a given angle 'italicAngle' and the pivotal height 'pivotalY',
		around which the italic slanting is executed, usually half x-height.
		Usage: myPoint = italicize(myPoint,10,xHeight*0.5)
		"""
		if Glyphs.boolDefaults["com.wwwhhhhh.ShowCrosshairOnSelect.ignoreItalicAngle"]:
			return thisPoint
		else:
			x = thisPoint.x
			yOffset = thisPoint.y - pivotalY  # calculate vertical offset
			italicAngle = radians(italicAngle)  # convert to radians
			tangens = tan(italicAngle)  # math.tan needs radians
			horizontalDeviance = tangens * yOffset  # vertical distance from pivotal point
			x += horizontalDeviance  # x of point that is yOffset from pivotal point
			return NSPoint(x, thisPoint.y)

	@objc.python_method
	def background(self, layer):
		toolEventHandler = self.controller.windowController().toolEventHandler()
		# toolIsDragging = toolEventHandler.dragging()
		toolIsTextTool = toolEventHandler.className() == "GlyphsToolText"
		toolIsToolHand = toolEventHandler.className() == "GlyphsToolHand"
		if any([toolIsTextTool, toolIsToolHand]):
			return

		crossHairCenter = self.selectionPosition(layer)
		if crossHairCenter is None:
			return

		# determine italic angle:
		italicAngle = 0.0
		try:
			thisMaster = layer.associatedFontMaster()
			italicAngle = thisMaster.italicAngle
		except:
			pass

		# set up bezierpath:
		offset = 1000000
		NSColor.disabledControlTextColor().set()  # subtle grey
		crosshairPath = NSBezierPath.bezierPath()
		crosshairPath.setLineWidth_(0.75 / self.getScale())

		# vertical line:
		crosshairPath.moveToPoint_(self.italicize(NSPoint(crossHairCenter.x, -offset), italicAngle=italicAngle, pivotalY=crossHairCenter.y))
		crosshairPath.lineToPoint_(self.italicize(NSPoint(crossHairCenter.x, +offset), italicAngle=italicAngle, pivotalY=crossHairCenter.y))

		# horizontal line:
		crosshairPath.moveToPoint_(NSPoint(-offset, crossHairCenter.y))
		crosshairPath.lineToPoint_(NSPoint(+offset, crossHairCenter.y))

		# set colour
		selectionColor = 0, 0.5, 0, 0.4
		NSColor.colorWithCalibratedRed_green_blue_alpha_(*selectionColor).set()

		# execute stroke:
		crosshairPath.stroke()

	@objc.python_method
	def selectionPosition(self, layer):
		# view = self.controller.graphicView()
		# selectionPosition = view.getActiveLocation_(Glyphs.currentEvent())
		try:
			selection = layer.selectionBounds
			if selection.origin.x < 1e15 and hasattr(selection, "origin"):
				selectionPosition_x, selectionPosition_y = selection.origin.x + selection.size.width / 2, selection.origin.y + selection.size.height / 2
				selectionPosition = NSPoint(selectionPosition_x, selectionPosition_y)
				return selectionPosition
			else:
				return None
		except:
			return None

	@objc.python_method
	def foregroundInViewCoords(self):
		toolEventHandler = self.controller.windowController().toolEventHandler()
		toolIsTextTool = toolEventHandler.className() == "GlyphsToolText"
		toolIsToolHand = toolEventHandler.className() == "GlyphsToolHand"

		if any([toolIsTextTool, toolIsToolHand]):
			return

		activeLayer = self.controller.activeLayer()
		if activeLayer is None:
			return

		selectionPosition = self.selectionPosition(activeLayer)
		if selectionPosition is None:
			return

		if Glyphs.boolDefaults["com.wwwhhhhh.ShowCrosshairOnSelect.showCoordinates"]:
			self.drawCoordinates(selectionPosition)

		if Glyphs.boolDefaults["com.wwwhhhhh.ShowCrosshairOnSelect.showThickness"]:
			self.drawThickness(activeLayer, selectionPosition)

	@objc.python_method
	def drawCoordinates(self, selectionPosition):

		coordinateText = "%4d, %4d" % (
			round(selectionPosition.x),
			round(selectionPosition.y)
		)

		fontSize = Glyphs.defaults["com.wwwhhhhh.ShowCrosshairOnSelect.fontSize"]
		fontAttributes = {
			#NSFontAttributeName: NSFont.labelFontOfSize_(10.0),
			NSFontAttributeName: NSFont.monospacedDigitSystemFontOfSize_weight_(fontSize, 0.0),
			NSForegroundColorAttributeName: NSColor.textColor()
		}
		displayText = NSAttributedString.alloc().initWithString_attributes_(
			coordinateText,
			fontAttributes
		)
		textAlignment = 0  # top left: 6, top center: 7, top right: 8, center left: 3, center center: 4, center right: 5, bottom left: 0, bottom center: 1, bottom right: 2
		#font = layer.parent.parent
		lowerLeftCorner = self.controller.viewPort.origin
		displayText.drawAtPoint_alignment_(lowerLeftCorner, textAlignment)

	@objc.python_method
	def drawThicknessBadge(self, fontSize, x, y, value):
		width = len(str(value)) * fontSize * 0.7
		rim = fontSize * 0.3
		badge = NSMakeRect(x - width / 2, y - fontSize / 2 - rim, width, fontSize + rim * 2)
		NSColor.textBackgroundColor().set()
		NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(badge, fontSize * 0.5, fontSize * 0.5).fill()

	@objc.python_method
	def drawThicknessText(self, thicknessFontAttributes, x, y, item):
		displayText = NSAttributedString.alloc().initWithString_attributes_(
			str(item),
			thicknessFontAttributes
		)
		displayText.drawAtPoint_alignment_(NSPoint(x, y), 4)

	def toggleShowCoordinates(self):
		self.toggleSetting("showCoordinates")

	def toggleShowThickness(self):
		self.toggleSetting("showThickness")

	@objc.python_method
	def toggleSetting(self, prefName):
		pref = "com.wwwhhhhh.ShowCrosshairOnSelect.%s" % prefName
		oldSetting = Glyphs.boolDefaults[pref]
		Glyphs.defaults[pref] = int(not oldSetting)
		self.generalContextMenus = self.buildContextMenus()

	# def addMenuItemsForEvent_toMenu_(self, event, contextMenu):
	# 	'''
	# 	The event can tell you where the user had clicked.
	# 	'''
	# 	try:
	#
	# 		if self.generalContextMenus:
	# 			setUpMenuHelper(contextMenu, self.generalContextMenus, self)
	#
	# 		newSeparator = NSMenuItem.separatorItem()
	# 		contextMenu.addItem_(newSeparator)
	#
	# 		contextMenus = self.conditionalContextMenus()
	# 		if contextMenus:
	# 			setUpMenuHelper(contextMenu, contextMenus, self)
	#
	# 	except:
	# 		import traceback
	# 		NSLog(traceback.format_exc())

	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
