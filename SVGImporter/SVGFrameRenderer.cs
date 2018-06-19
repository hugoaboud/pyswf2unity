// Copyright (C) 2015 Jaroslav Stehlik - All Rights Reserved
// This code can only be used under the standard Unity Asset Store End User License Agreement
// A Copy of the EULA APPENDIX 1 is available at http://unity3d.com/company/legal/as_terms


using SVGImporter.Geometry;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Serialization;

namespace SVGImporter
{
    [ExecuteInEditMode]
    [AddComponentMenu("Rendering/SVG Frame Renderer", 20)]
    public class SVGFrameRenderer : SVGRenderer
    {
        [FormerlySerializedAs("frame")]
        [SerializeField]
        protected float _frame;
        protected float _lastFrame;

        [FormerlySerializedAs("length")]
        [SerializeField]
        protected int _length = 0;
        
        protected Dictionary<int, SVGLayer> frames = null;

        protected override void PrepareForRendering(bool force = false)
        {
            if (_lastFrame != _frame) base.PrepareForRendering(true);
            base.PrepareForRendering(force);
            _lastFrame = _frame;
        }

        protected override void GenerateMesh()
        {
            if (frames == null || (_lastVectorGraphics != _vectorGraphics))
            {
                frames = new Dictionary<int, SVGLayer>();
                foreach (SVGLayer layer in _layers)
                {
                    System.String[] split = layer.name.Split(':');
                    if (split.Length > 1)
                    {
                        if (split[0] == "f")
                        {
                            int f;
                            if (System.Int32.TryParse(split[1], out f))
                            {
                                frames.Add(f, layer);
                            }
                        }
                    }
                }
                _length = frames.Count;
            }
            Shader[] outputShaders;
            if (frames.ContainsKey((int)_frame)) {
                SVGLayer[] frameLayer = { frames[(int)_frame] };
                SVGMesh.CombineMeshes(frameLayer, _mesh, out outputShaders, _vectorGraphics.useGradients, _vectorGraphics.format, _vectorGraphics.compressDepth, _vectorGraphics.antialiasing);
            }
            else
                SVGMesh.CombineMeshes(_layers, _mesh, out outputShaders, _vectorGraphics.useGradients, _vectorGraphics.format, _vectorGraphics.compressDepth, _vectorGraphics.antialiasing);
        }
    }
}