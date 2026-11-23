"""Party-M-0001 + ActorCore mocap (Idle, Stand Talk) -> party-m.glb for Humex.
Run: Blender -b --factory-startup --python actorcore_to_glb.py -- <character.fbx> <idle.fbx> <talk.fbx> <out.glb> <preview_prefix> [<texture set folder>]
The optional texture set folder (e.g. "Texture sets/Actor/party-m-0001/02") picks an outfit colour variant.
"""
import bpy, sys, os, math, random
args = sys.argv[sys.argv.index("--")+1:]
char_fbx, idle_fbx, talk_fbx, out, preview = args[:5]
outfit = args[5] if len(args) > 5 else None
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
maps = {"Roughness": os.path.join(tex, "Character_roughness.jpg"), "Metallic": os.path.join(tex, "Character_metallic.jpg")}
if outfit:                                              # swap in an ActorCore colour variant (same UV layout)
    maps = {"Roughness": os.path.join(outfit, "Roughness.jpg"), "Metallic": os.path.join(outfit, "Metallic.jpg")}
    for l in nt.links:
        if l.to_socket == bsdf.inputs["Base Color"]: l.from_node.image = bpy.data.images.load(os.path.join(outfit, "Diffuse.jpg"))
        if l.to_node.type == "NORMAL_MAP" and l.from_node.type == "TEX_IMAGE":
            l.from_node.image = bpy.data.images.load(os.path.join(outfit, "Normal.jpg")); l.from_node.image.colorspace_settings.name = "Non-Color"
for sock, path in maps.items():
    node = nt.nodes.new("ShaderNodeTexImage"); node.image = bpy.data.images.load(path)
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


from mathutils import Matrix, Vector
def head_yaw():
    pb = arm.pose.bones["CC_Base_Head"]
    M = (arm.matrix_world @ pb.matrix).to_3x3(); R = (arm.matrix_world @ pb.bone.matrix_local).to_3x3()
    f = (M @ R.inverted()) @ Vector((0, -1, 0))
    return math.degrees(math.atan2(f.x, -f.y))

def face_forward(act, end):
    """The ActorCore Idle clip keeps the head turned ~30 deg to one side: turn it back to face the camera."""
    arm.animation_data.action = act
    if getattr(arm.animation_data, "action_slot", None) is None and getattr(act, "slots", None): arm.animation_data.action_slot = act.slots[0]
    pb = arm.pose.bones["CC_Base_Head"]
    yaws = []
    for f in range(1, end + 1, 5): scene.frame_set(f); yaws.append(head_yaw())
    corr = -sum(yaws) / len(yaws)
    for f in range(1, end + 1):
        scene.frame_set(f)
        M = pb.matrix.copy(); h = M.translation.copy()
        pb.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(corr), 4, "Z") @ Matrix.Translation(-h) @ M
        pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == "QUATERNION" else "rotation_euler", frame=f)
    scene.frame_set(1); print("HEAD", act.name, "turned", round(corr, 1), "deg; now", round(head_yaw(), 1))
    arm.animation_data.action = None

arm.animation_data_create()
for name, path, talk in (("Idle", idle_fbx, False), ("Talk", talk_fbx, True)):
    act = import_motion(path); act.name = name
    end = int(act.frame_range[1])
    if not talk: face_forward(act, end)
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
for tr in arm.animation_data.nla_tracks: tr.mute = tr.name != "Idle"
for tr in mesh.data.shape_keys.animation_data.nla_tracks: tr.mute = tr.name != "Idle"
for fr in (170,):
    scene.frame_set(fr); scene.render.filepath = f"{preview}_idle_{fr}.png"; bpy.ops.render.render(write_still=True)
for tr in list(arm.animation_data.nla_tracks) + list(mesh.data.shape_keys.animation_data.nla_tracks): tr.mute = False
bpy.data.objects.remove(cam); bpy.data.objects.remove(sun)
scene.frame_set(1)

bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_animation_mode="NLA_TRACKS",
    export_morph=True, export_morph_normal=False, export_skins=True, export_image_format="WEBP",
    export_apply=False, export_force_sampling=True, export_frame_step=2)
print("DONE", out)
