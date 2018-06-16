## pySWF2Unity
### a lib for converting .swf vector animations to .svg + .anim (for Unity)

##### dependencies
* pyswf
* pyyaml

##### features
* [DefineShape*] and [DefineMorphShape] shapes to SVG
* Position, Scale and Euler Keyframes
* IsActive Keyframes for Shapes that change depth
* Keyframe 0 with default value
* Repeated Keyframe cleanup

##### todo + known bugs
* Optional SVG layering for shapes that share depth
* Messed up scale/position of elements on Unity (?)
* MorphShape color is wrong, should come from fillStyles
* Clean unnecessary IsActive Keyframes

##### no-features

* Images
* Shape morphs (start shape is exported to SVG)