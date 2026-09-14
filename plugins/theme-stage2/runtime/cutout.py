"""Conservative reserved-matte removal for generated independent asset images.

No global recoloring, texture flattening, source scene editing, or recomposition.
"""
import re
import numpy as np
from scipy import ndimage as ndi
from PIL import Image

VERSION='1.0.0'

def remove_matte(image, matte='auto', shadowed_matte=False):
    a=np.asarray(image.convert('RGB'),dtype=np.float32)
    edge=np.concatenate([a[:8].reshape(-1,3),a[-8:].reshape(-1,3),
                         a[:,:8].reshape(-1,3),a[:,-8:].reshape(-1,3)])
    estimated=np.median(edge,axis=0)
    if matte=='auto':
        if not (estimated[0]>200 and estimated[2]>200 and estimated[1]<80):
            raise ValueError('No unambiguous magenta matte detected; inspect or regenerate a uniform reserved backdrop. Do not key a checkerboard or a white character backdrop blindly.')
        key=estimated
    elif re.fullmatch(r'#[0-9a-fA-F]{6}',matte):
        key=np.array([int(matte[i:i+2],16) for i in (1,3,5)],dtype=np.float32)
    else:
        raise ValueError('Matte must be auto or a #RRGGBB color')
    uniformity=float(np.mean(np.max(np.abs(edge-key),axis=1)<70))
    if uniformity<.90:
        raise ValueError('Backdrop is not sufficiently uniform for conservative keying')
    r,g,b=a[:,:,0],a[:,:,1],a[:,:,2]
    magenta=bool(key[0]>180 and key[2]>180 and key[1]<100)
    if shadowed_matte and not magenta:
        raise ValueError('Shadowed-matte cleanup is only supported for an inspected magenta backdrop')
    if magenta:
        bg=(r>185)&(b>185)&(g<90)&(np.abs(r-b)<50)
    else:
        bg=np.max(np.abs(a-key),axis=2)<70
    if shadowed_matte:
        bg|=(r>105)&(b>95)&(g<110)&(r-g>75)&(b-g>55)&(np.abs(r-b)<100)
    labels,_=ndi.label(~bg);sizes=np.bincount(labels.ravel())
    body=(~bg)&(sizes[labels]>=12)
    core=ndi.binary_erosion(body,iterations=2)
    if not core.any():
        raise ValueError('No reliable foreground remains; refusing to export an empty or lost asset')
    distance,indices=ndi.distance_transform_edt(~core,return_indices=True)
    nearest=a[indices[0],indices[1]];vec=nearest-key
    alpha=np.clip(np.sum((a-key)*vec,axis=2)/np.maximum(np.sum(vec*vec,axis=2),1),0,1)
    alpha[core]=1;alpha[distance>6]=0;alpha[alpha<.025]=0;alpha[alpha>.99]=1
    if shadowed_matte:
        alpha[(r-g>25)&(b-g>25)]=0
    rgb=a.copy();partial=(alpha>0)&(alpha<1)
    rgb[partial]=nearest[partial];rgb[alpha==0]=0
    out=Image.fromarray(np.dstack([np.rint(rgb).astype(np.uint8),np.rint(alpha*255).astype(np.uint8)]),'RGBA')
    box=out.getchannel('A').getbbox()
    if box is None:
        raise ValueError('Empty alpha output')
    padding=16
    trimmed=Image.new('RGBA',(box[2]-box[0]+2*padding,box[3]-box[1]+2*padding))
    trimmed.alpha_composite(out.crop(box),(padding,padding))
    return trimmed,{'method':'reserved matte with nearest opaque edge-color reconstruction',
        'algorithm_version':VERSION,'estimated_matte_rgb':key.tolist(),'border_match_fraction':uniformity,
        'raw_visible_bbox':list(box),'padding':padding,'shadowed_matte_cleanup':shadowed_matte,
        'interior_recoloring':False,'scope':'Alpha and antialiased edges only; not an art-style correction.'}
