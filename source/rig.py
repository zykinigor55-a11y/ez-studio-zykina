"""Add a preliminary articulated skeleton, four skin weights and test action to V6 GLB.
Rest pose is the original model pose; weights are automatic and require artistic refinement.
"""
import json, struct, math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent.parent
src=ROOT/'model'/'01_ded_moroz.glb'
raw=src.read_bytes(); n=struct.unpack_from('<I',raw,12)[0]; doc=json.loads(raw[20:20+n]); data=bytearray(raw[28+n:]); data=data[:doc['buffers'][0]['byteLength']]

def add(a, typ, ct, target=None):
    while len(data)%4: data.append(0)
    offset=len(data); a=np.ascontiguousarray(a); b=a.tobytes(); data.extend(b)
    view={'buffer':0,'byteOffset':offset,'byteLength':len(b)}
    if target: view['target']=target
    doc['bufferViews'].append(view); acc={'bufferView':len(doc['bufferViews'])-1,'componentType':ct,'count':len(a),'type':typ}
    if typ=='SCALAR' and ct==5126: acc['min']=[float(a.min())];acc['max']=[float(a.max())]
    doc['accessors'].append(acc); return len(doc['accessors'])-1

def read(i):
    a=doc['accessors'][i];v=doc['bufferViews'][a['bufferView']];return np.frombuffer(data,dtype='<f4',offset=v.get('byteOffset',0)+a.get('byteOffset',0),count=a['count']*3).reshape(-1,3).copy()

bones=[]; parents=[]; points=[]
def bone(name,p,parent=-1):
    bones.append(name);parents.append(parent);points.append(np.array(p,float));return len(bones)-1
root=bone('Root',(0,0,0));hip=bone('Pelvis',(0,.82,0),root);sp=bone('Spine',(0,1.04,0),hip);ch=bone('Chest',(0,1.32,0),sp);neck=bone('Neck',(0,1.46,0),ch);head=bone('Head',(0,1.62,0),neck)
ends={head:np.array([0,1.91,0])}; groups={}
for side,s in [('L',1),('R',-1)]:
    cl=bone('Clavicle.'+side,(s*.13,1.38,0),ch);up=bone('UpperArm.'+side,(s*.25,1.39,-.02),cl);el=bone('Forearm.'+side,(s*.32,1.12,.18),up);hand=bone('Hand.'+side,(s*.22,1.25,.37),el)
    ends[hand]=np.array([s*.22,1.25,.445]); fingers=[]
    for j,name in enumerate(['Index','Middle','Ring','Pinky']):
        x=s*(.22+(j-1.5)*.018);p=hand
        for k,z in enumerate([.439,.455,.472]):
            p=bone(f'{name}.{k+1}.{side}',(x,1.25,z),p);fingers.append(p)
        ends[p]=np.array([x,1.25,.485])
    p=hand
    for k,(x,y,z) in enumerate([(s*.187,1.263,.408),(s*.17,1.265,.430),(s*.161,1.265,.447)]):
        p=bone(f'Thumb.{k+1}.{side}',(x,y,z),p);fingers.append(p)
    ends[p]=np.array([s*.153,1.265,.455])
    thigh=bone('Thigh.'+side,(s*.105,.82,0),hip);shin=bone('Shin.'+side,(s*.105,.43,0),thigh);foot=bone('Foot.'+side,(s*.105,.105,0),shin);toe=bone('Toe.'+side,(s*.105,.065,.115),foot);ends[toe]=np.array([s*.105,.055,.18]);groups[side]=(up,el,hand,fingers,thigh,shin,foot,toe)
P=np.array(points); start=len(doc['nodes']); nodes=[]
for i,name in enumerate(bones):
    n={'name':name,'translation':(P[i]-(P[parents[i]] if parents[i]>=0 else 0)).tolist()}; children=[start+j for j,p in enumerate(parents) if p==i]
    if children:n['children']=children
    nodes.append(n)
doc['nodes']+=nodes;doc['nodes'][0].setdefault('children',[]).append(start)
# Inverse bind matrices (glTF column-major).
ib=np.tile(np.eye(4,dtype=np.float32),(len(P),1,1));ib[:,3,:3]=-P
inv=add(ib,'MAT4',5126);doc['skins']=[{'name':'DedMoroz_AutoRig_v01','inverseBindMatrices':inv,'skeleton':start,'joints':list(range(start,start+len(P)))}];doc['nodes'][1]['skin']=0
pr=doc['meshes'][0]['primitives'][0];v=read(pr['attributes']['POSITION']);n=len(v)
# Distance to bone segment; spatial constraints keep head/face attached to head and prevent cross-body influences.
dist=np.empty((n,len(P)),np.float32)
for i in range(len(P)):
    children=[j for j,p in enumerate(parents) if p==i];a=P[i];b=ends.get(i,P[children[0]] if children else a+np.array([0,.04,0]));d=b-a; t=np.clip((v-a)@d/max(np.dot(d,d),1e-10),0,1);dist[:,i]=np.linalg.norm(v-a-t[:,None]*d,axis=1)
dist[:,root]=100
for side,s in [('L',1),('R',-1)]:
    up,el,hand,fs,thigh,shin,foot,toe=groups[side]; opposite=(v[:,0]*s<-.015);dist[np.ix_(opposite,[up,el,hand,*fs,thigh,shin,foot,toe])]=100
    nothand=(v[:,2]<.365)|(v[:,1]<1.19)|(v[:,1]>1.32);dist[np.ix_(nothand,fs)]=100
    notarm=(v[:,1]<.92)|(v[:,1]>1.48)|((np.abs(v[:,0])<.15)&(v[:,2]<.29));dist[np.ix_(notarm,[up,el,hand,*fs])]=100
    notleg=v[:,1]>1.0;dist[np.ix_(notleg,[thigh,shin,foot,toe])]=100
idx=np.argsort(dist,axis=1)[:,:4]; ds=np.take_along_axis(dist,idx,axis=1); w=1/np.maximum(ds,.012)**4;w/=w.sum(1,keepdims=True)
mask=v[:,1]>1.51;idx[mask]=[head,neck,sp,ch];w[mask]=[1,0,0,0]
pr['attributes']['JOINTS_0']=add(idx.astype('<u2'),'VEC4',5123,34962);pr['attributes']['WEIGHTS_0']=add(w.astype('<f4'),'VEC4',5126,34962)
# A small test clip: turn head, bend forearm, curl fingers. Not a finished performance.
times=np.array([0,.7,1.4,2.1,3],'<f4'); ti=add(times,'SCALAR',5126);sam=[];channels=[]
def anim(name,axis,angles):
    a=np.radians(angles)/2; q=np.zeros((len(a),4),'<f4');q[:,:3]=np.sin(a)[:,None]*np.array(axis);q[:,3]=np.cos(a);ai=add(q,'VEC4',5126);sam.append({'input':ti,'output':ai,'interpolation':'LINEAR'});channels.append({'sampler':len(sam)-1,'target':{'node':start+bones.index(name),'path':'rotation'}})
anim('Head',[0,1,0],[0,9,0,-7,0]);anim('Forearm.R',[1,0,0],[0,-12,-20,-8,0]);anim('Hand.R',[1,0,0],[0,6,12,4,0])
for name in ['Index','Middle','Ring','Pinky']:
    for j in range(1,4):anim(f'{name}.{j}.R',[1,0,0],[0,8,23,12,0])
doc['animations']=[{'name':'Rig motion test — 3s','samplers':sam,'channels':channels}];doc['buffers'][0]['byteLength']=len(data)
j=json.dumps(doc,separators=(',',':')).encode();j+=b' '*((-len(j))%4);data+=b'\x00'*((-len(data))%4)
out=ROOT/'model'/'ded_moroz_rig_v01.glb';out.write_bytes(struct.pack('<4sII',b'glTF',2,12+8+len(j)+8+len(data))+struct.pack('<I4s',len(j),b'JSON')+j+struct.pack('<I4s',len(data),b'BIN\x00')+data)
assert np.allclose(w.sum(1),1) and idx.max()<len(bones)
(ROOT/'model'/'rig_manifest.json').write_text(json.dumps({'joints':len(bones),'vertices':n,'triangles':doc['accessors'][pr['indices']]['count']//3,'skin_weights_per_vertex':4,'animation_seconds':3,'bone_names':bones,'limitations':'Automatic draft weights; no IK, face rig, cloth simulation or hand retopology. Visual deformation not validated.'},indent=2))
print(out, len(bones),n,out.stat().st_size)
