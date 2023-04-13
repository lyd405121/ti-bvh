import sys
import os
import math
import taichi as ti
import TriMesh as TriMesh

ti.init(arch=ti.cpu)
draw_line     =  ti.Vector.field(3, float,shape=4)
draw_particle =  ti.Vector.field(3, float,shape=5)

frame       = 0
window      = ti.ui.Window('Bvh', (1280, 720), vsync=False)
canvas      = window.get_canvas()
scene       =  ti.ui.Scene()
camera      = ti.ui.make_camera()
imgui       = window.get_gui()
imgui.slider_float('Radius', 1, 1, 50)


tri_mesh = TriMesh.TriMesh()
tri_mesh.add_obj("model/Test.obj")
#tri_mesh.add_obj("model/Simple.obj")
#tri_mesh.add_obj("model/Normal.obj")
#tri_mesh.add_obj("model/Large.obj")
tri_mesh.setup_layout()
tri_mesh.update_to_device()
tri_mesh.build_bvh()
tri_mesh.setup_vert()
#tri_mesh.write_bvh()


center = tri_mesh.get_center()
size   = tri_mesh.get_size()
max_dis= max(max(size[0],size[1]),size[2])
particle_r  = max_dis * 0.02


#rotate the camera by angle
is_mesh_show_old   = 1
is_bvh_show_old    = 0
def MeshControl():
    global is_mesh_show_old,is_bvh_show_old
    imgui.text("Mesh Control")
    is_mesh_show_new   = imgui.checkbox('Show Mesh', is_mesh_show_old)
    is_bvh_show_new   = imgui.checkbox('Show Bvh', is_bvh_show_old)
    is_mesh_show_old = is_mesh_show_new
    is_bvh_show_old  = is_bvh_show_new
    if is_mesh_show_new:
        scene.mesh(tri_mesh.tri_mesh, color=(0.5, 0.5, 0.5),show_wireframe=True)
    if is_bvh_show_new :
        scene.lines(tri_mesh.line_bvh,indices=tri_mesh.indice_bvh, color=(1.0, 1.0, 1.0),width =1)

#rotate the camera by angle
old_yaw   = 0.0
old_pitch = 0.0
def CameraControl():
    global old_yaw,old_pitch,size,center
    imgui.text("Camera Control")
    new_yaw     = imgui.slider_float('Camera Yaw', old_yaw, 0.0, 6.28)
    new_pitch   = imgui.slider_float('Camera Pitch', old_pitch, -1.5, 1.5)
    old_yaw     = new_yaw 
    old_pitch   = new_pitch

    radius = max_dis*2.0
    eye    = [math.sin(old_yaw)*math.cos(new_pitch)*radius, math.sin(new_pitch)*radius, math.cos(old_yaw)*math.cos(new_pitch)*radius]
    camera.position(eye[0],eye[1],eye[2])
    camera.lookat(center[0], center[1],center[2])
    camera.up(0.0, 1.0, 0.0)
    camera.z_near(radius * 0.001)
    camera.z_far(radius*10.0)

#a ray to intersect the mesh
old_origin_x  = 0.0
old_origin_y  = 0.0
old_origin_z  = 0.0
old_target_x = max_dis
old_target_y = 0.0
old_target_z = 0.0
is_center_old   = 1
def RayControl():
    global old_origin_x,old_origin_y,old_origin_z,size,center,is_center_old,old_target_x,old_target_y,old_target_z
    imgui.text("Ray Control")
    is_center_new   = imgui.checkbox('Towards Center', is_center_old)
    is_center_old   = is_center_new

    new_origin_x     = imgui.slider_float('Origin x', old_origin_x,   -max_dis*2.0, max_dis*2.0)
    new_origin_y     = imgui.slider_float('Origin y', old_origin_y,   -max_dis*2.0, max_dis*2.0)
    new_origin_z     = imgui.slider_float('Origin z', old_origin_z,   -max_dis*2.0, max_dis*2.0)
    old_origin_x     = new_origin_x 
    old_origin_y     = new_origin_y
    old_origin_z     = new_origin_z

    new_target_x    = imgui.slider_float('Target x', old_target_x,  -max_dis*2.0, max_dis*2.0)
    new_target_y    = imgui.slider_float('Target y', old_target_y,  -max_dis*2.0, max_dis*2.0)
    new_target_z    = imgui.slider_float('Target z', old_target_z,  -max_dis*2.0, max_dis*2.0)
    old_target_x    = new_target_x 
    old_target_y    = new_target_y
    old_target_z    = new_target_z


    start           = [new_origin_x, new_origin_y, new_origin_z]
    target          = [new_target_x, new_target_y, new_target_z] 
    end             = [0]*3


    norm = 0.0
    dir = [0,0,0]
    for i in range(3):
        if is_center_new == 1:
            end[i] = center[i]
        else:
            end[i] = target[i]
        dir[i] = end[i] - start[i]
        norm  += dir[i]*dir[i]
    if norm < 0.001:
        dir = [0,1,0]
    else:
        norm = math.sqrt(norm)
        dir = [dir[0]/norm,dir[1]/norm,dir[2]/norm]

    res_hit  = tri_mesh.bvh.ray_trace_cpu(ti.Vector([start[0], start[1],start[2]]), ti.Vector([dir[0], dir[1],dir[2]]))
    res_sd   = tri_mesh.bvh.singed_distance_cpu(ti.Vector([target[0],target[1],target[2]]))


    line_np       = draw_line.to_numpy()
    particle_np   = draw_particle.to_numpy()

    for i in range(3):
        line_np[0,i] =  start[i]
        line_np[1,i] =  end[i]
        line_np[2,i] =  target[i]
        line_np[3,i] =  target[i] + res_sd[4+i]* particle_r*3.0
        particle_np[0, i] = start[i]
        particle_np[1, i] = end[i]
        particle_np[2, i] = target[i]
        particle_np[3, i] = res_hit[i+1]
        particle_np[4, i] = res_sd[i+1]
    draw_line.from_numpy(line_np)
    draw_particle.from_numpy(particle_np)

    imgui.text("Intersect Result")
    if res_hit[0] < 100000.0:
        hit_dis         = "Hit Distance:%.3f"%res_hit[0]
        hit_point_str   = "Hit Point:%.3f,%.3f,%.3f"%(res_hit[1],res_hit[2],res_hit[3])
        imgui.text(hit_dis)
        imgui.text(hit_point_str)
        scene.lines(draw_line,  color=(1.0, 0.0, 0.0), vertex_offset=0,vertex_count=2,width = 10)
        scene.particles(draw_particle, color=(1.0, 0.0, 0.0),  index_offset=0,index_count=2, radius = particle_r)
        scene.particles(draw_particle, color=(0.0, 0.0, 1.0),  index_offset=3,index_count=1, radius = particle_r)
    else:
        imgui.text("Hit None")
        imgui.text("Hit None")      
        scene.lines(draw_line,  color=(0.0, 1.0, 0.0), vertex_offset=0,vertex_count=2,width = 5)
        scene.particles(draw_particle, color=(0.0, 1.0, 0.0),  index_offset=0,index_count=2, radius = particle_r)

    if res_sd[0] > 0.0:
        scene.lines(draw_line,  color=(0.0, 1.0, 0.0), vertex_offset=2,vertex_count=2,width = 2)
        scene.particles(draw_particle, color=(0.0, 1.0, 0.0),  index_offset=2,index_count=1, radius = particle_r)
        scene.particles(draw_particle, color=(1.0, 1.0, 0.0),  index_offset=4,index_count=1, radius = particle_r)
    else:
        scene.lines(draw_line,  color=(1.0, 0.0, 0.0), vertex_offset=2,vertex_count=2,width = 2)
        scene.particles(draw_particle, color=(1.0, 0.0, 0.0),  index_offset=2,index_count=1, radius = particle_r)
        scene.particles(draw_particle, color=(1.0, 1.0, 0.0),  index_offset=4,index_count=1, radius = particle_r)


    imgui.text("Signed Distance:%.3f"%res_sd[0])
    imgui.text("Closest Point:%.3f %.3f %.3f"%(res_sd[1],res_sd[2],res_sd[3]))
    imgui.text("Closest Normal:%.3f %.3f %.3f"%(res_sd[4],res_sd[5],res_sd[6]))

while window.running:
    MeshControl()

    if frame > -1:
    #if frame < 1:
        CameraControl()
        RayControl()

    #camera.track_user_inputs(window, movement_speed=0.03, hold_key=ti.ui.LMB)
    scene.point_light(pos=(10.0, 10.0, 10.0), color=(1.0,1.0,1.0))
    scene.point_light(pos=(-10.0, -10.0, -10.0), color=(1.0,1.0,1.0))
    scene.set_camera(camera)
    canvas.scene(scene)
    window.show()

    frame+=1