// Copyright (C) 2015 Jaroslav Stehlik - All Rights Reserved
// This code can only be used under the standard Unity Asset Store End User License Agreement
// A Copy of the EULA APPENDIX 1 is available at http://unity3d.com/company/legal/as_terms

//#define PATH_COMMAND_DEBUG

using UnityEngine;
using System.Collections;
using System.Collections.Generic;

namespace SVGImporter.Rendering 
{
    using Document;

    public class SVGGroupElement : SVGElement, ISVGDrawable
    {
        private SVGLayer _layer;
        public SVGLayer layer
        {
            get
            {
                return _layer;
            }
        }

        public void CreateLayer()
        {
            _layer = new SVGLayer();
            _layer.name = name;
            _layer.shapes = new SVGShape[0];
            SVGGraphics.currentGroup = this;
        }

        public SVGGroupElement(SVGParser xmlImp,
                    SVGTransformList inheritTransformList,
                    SVGPaintable inheritPaintable) : base(xmlImp, inheritTransformList, inheritPaintable)
        {
            _name = attributeList.GetValue("id");
        }

        public new void Render()
        {
            if (!string.IsNullOrEmpty(name)) CreateLayer();
            for (int i = 0; i < elementList.Count; i++)
            {
                ISVGDrawable temp = elementList[i] as ISVGDrawable;
                if (temp != null)
                {
                    temp.Render();
                    SVGGraphics.currentGroup = this;
                }
            }
            if (SVGGraphics.currentGroup == this) SVGGraphics.currentGroup = null;
            if (_layer.shapes != null && _layer.shapes.Length > 0) SVGGraphics.AddLayer(_layer);
        }

        public void AddShapes(SVGShape[] shapes)
        {
            SVGShape[] current = new SVGShape[_layer.shapes.Length];
            _layer.shapes.CopyTo(current, 0);
            _layer.shapes = new SVGShape[current.Length + shapes.Length];
            current.CopyTo(_layer.shapes, 0);
            shapes.CopyTo(_layer.shapes, current.Length);
        }
    }
}