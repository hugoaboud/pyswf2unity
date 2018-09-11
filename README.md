## pySWF2Unity
### a lib for converting .swf vector animations to .svg + .anim (for Unity)

##### dependencies
* pyswf
* pyyaml

##### features
* [DefineShape*] and [DefineMorphShape] tags to SVG
* [PlaceObject] tags to Position, Scale, Euler and IsActive Keyframes
* Curve optimization: Keyframe 0 with default value
* Curve optimization: Repeated Keyframe cleanup
* Optional grouping by depth
* Optional exporting multiple frames on a single .svg file
* Curve optimization: Remove last if only two equal keyframes
* Curve optimization: Remove default keyframe if it's the only one
* FrameKeyframe for animating depth group on Unity (customizable path)
* Integration with SVG Importer for animated SVG files

##### todo + known bugs
* Optional center around first frame of selected character
* BUG: MorphShape color is wrong, should come from fillStyles

##### no-features
* Images
* Shape morphs (start shape is exported to SVG)
