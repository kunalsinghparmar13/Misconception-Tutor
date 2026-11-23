"""Party-M-0001 + ActorCore mocap (Idle, Stand Talk) -> party-m.glb for Humex.
Run: Blender -b --factory-startup --python actorcore_to_glb.py -- <character.fbx> <idle.fbx> <talk.fbx> <out.glb> <preview_prefix>
"""
import bpy, sys, os, math, random
args = sys.argv[sys.argv.index("--")+1:]
char_fbx, idle_fbx, talk_fbx, out, preview = args
random.seed(7)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
bpy.ops.import_scene.fbx(filepath=char_fbx)
scene.render.fps = 60                                   # ActorCore motions are 60 fps
arm = bpy.data.objects["Armature"]
mesh = next(o for o in bpy.data.objects if o.type == "MESH")
for a in list(bpy.data.actions): bpy.data.actions.remove(a)
arm.animation_data_clear()

# Material: connect the roughness/metallic maps the FBX import leaves out, render opaque.
tex = os.path.join(os.path.dirname(char_fbx), "textures/party-m-0001/party-m-0001/Cesar_D_LaTorre_Jacket/Character")
mat = bpy.data.materials["Character"]; nt = mat.node_tree; bsdf = nt.nodes["Principled BSDF"]
for sock, fname in (("Roughness", "Character_roughness.jpg"), ("Metallic", "Character_metallic.jpg")):
    node = nt.nodes.new("ShaderNodeTexImage"); node.image = bpy.data.images.load(os.path.join(tex, fname))
    node.image.colorspace_settings.name = "Non-Color"; nt.links.new(node.outputs["Color"], bsdf.inputs[sock])
bsdf.inputs["Specular IOR Level"].default_value = 0.5
for l in list(nt.links):
    if l.to_socket == bsdf.inputs["Alpha"]: nt.links.remove(l)
for img in bpy.data.images:
    if img.size[0] > 2048: img.scale(2048, 2048)

def import_motion(path):
    """Import an ActorCore motion FBX and return its action (same CC_Base_* bone names as the character)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    act = next(o for o in new if o.type == "ARMATURE").animation_data.action
    for o in new: bpy.data.objects.remove(o)
    return act

keys = mesh.data.shape_keys.key_blocks
def face_action(name, end, talk):
    sk = mesh.data.shape_keys; sk.animation_data_create()
    act = bpy.data.actions.new(name + "_face"); sk.animation_data.action = act
    used = ["Eyes_Blink", "Mouth_Smile", "V_Open", "V_Wide", "V_Tight-O", "V_Explosive", "V_Dental_Lip", "V_Lip_Open", "V_Tight", "V_Affricate", "A25_Jaw_Open"]
    def setk(n, v, f): keys[n].value = v; keys[n].keyframe_insert("value", frame=f)
    for n in used: setk(n, 0.0, 1); setk(n, 0.0, end)
    setk("Mouth_Smile", 0.15, 1); setk("Mouth_Smile", 0.15, end)
    f = 90
    while f < end - 12:                                     # natural blinks every ~2.5-5 s
        setk("Eyes_Blink", 0, f); setk("Eyes_Blink", 1, f+5); setk("Eyes_Blink", 0, f+11)
        f += random.randint(150, 300)
    if talk:                                                # lip shapes while speaking (the mocap has no face data)
        visemes = ["V_Open", "V_Wide", "V_Tight-O", "V_Explosive", "V_Dental_Lip", "V_Lip_Open", "V_Affricate", "V_Open", "V_Tight"]
        f, prev = 4, None
        while f < end - 14:
            v = random.choice([x for x in visemes if x != prev]); prev = v
            amt = random.uniform(0.45, 0.9)
            setk(v, 0, f); setk(v, amt, f+6); setk(v, 0, f+14)
            setk("A25_Jaw_Open", 0, f); setk("A25_Jaw_Open", amt*0.35, f+6); setk("A25_Jaw_Open", 0, f+14)
            f += random.choice([8, 10, 12]) if random.random() > 0.12 else 22
    sk.animation_data.action = None
    return act

arm.animation_data_create()
for name, path, talk in (("Idle", idle_fbx, False), ("Talk", talk_fbx, True)):
    act = import_motion(path); act.name = name
    end = int(act.frame_range[1])
    t = arm.animation_data.nla_tracks.new(); t.name = name
    s = t.strips.new(name, 1, act)
    fa = face_action(name, end, talk)
    t2 = mesh.data.shape_keys.animation_data.nla_tracks.new(); t2.name = name
    t2.strips.new(name, 1, fa)
    print("MOTION", name, end)

# Previews: a few frames of Talk from the front.
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); scene.collection.objects.link(cam)
cam.location = (0, -1.92, 1.39); cam.rotation_euler = (math.radians(90), 0, 0)
cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24; cam.data.lens = 35.9; scene.camera = cam
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN")); sun.data.energy = 3; sun.rotation_euler = (math.radians(50), 0, math.radians(20)); scene.collection.objects.link(sun)
scene.world = bpy.data.worlds.new("W"); scene.world.color = (0.6, 0.6, 0.6)
scene.render.resolution_x, scene.render.resolution_y = 600, 800
for tr in arm.animation_data.nla_tracks: tr.mute = tr.name != "Talk"
for tr in mesh.data.shape_keys.animation_data.nla_tracks: tr.mute = tr.name != "Talk"
for fr in (1, 400, 900):
    scene.frame_set(fr); scene.render.filepath = f"{preview}_talk_{fr}.png"; bpy.ops.render.render(write_still=True)
for tr in list(arm.animation_data.nla_tracks) + list(mesh.data.shape_keys.animation_data.nla_tracks): tr.mute = False
bpy.data.objects.remove(cam); bpy.data.objects.remove(sun)
scene.frame_set(1)

bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_animation_mode="NLA_TRACKS",
    export_morph=True, export_morph_normal=False, export_skins=True, export_image_format="WEBP",
    export_apply=False, export_force_sampling=True, export_frame_step=2)
print("DONE", out)
