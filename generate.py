import bpy
import math
import mathutils
import random
import bmesh
import os
import shutil

# Paths and directories
base_path = os.getcwd()
output_path = os.path.join(base_path, "Output")
input_path_materials = os.path.join(base_path, "Materials")
input_base_images_path = os.path.join(input_path_materials, "Base")
input_floor_images_path = os.path.join(input_path_materials, "Floor")
fallback_material_path = os.path.join(input_floor_images_path, "fallback")

# Clear selection before starting script
bpy.ops.object.select_all(action="DESELECT")

# Assign initial objects to variables for easier reference
piece = bpy.data.objects["PieceSection"]
sun = bpy.data.objects["Sun"]
camera = bpy.data.objects["Camera"]
floor = bpy.data.objects["Floor"]

# Global lists used in multiple methods
pieces = []
modifier_froms = []
modifier_tos = []

# Stores positions in (x, y, z) of each modifier's starting position
modifier_positions = [
    # Corners
    [1,1,0],
    [1,-1,0],
    [-1,-1,0],
    [-1,1,0],
    
    # In/out connectors
    [0, -1.4, 0],
    [0, 1.4, 0],
    [-1.4, 0, 0],
    [1.4, 0, 0]
]

# Random variables used in multiple methods, automatically modified at runtime.
piece_overall_scale = 0
piece_end_scale = 0

# ENVIRONMENT RANDOM LIMITS
# =========================
# Sun rotation in degrees on XYZ between this and -this.
# 0 for no rotation. Values 180 or above will cause unrealistic shadows.
sun_rotation_limit_degrees = 50

# Sun light intensity randomised between these two values.
# Values below 3.5 result in a very dark image.
# Values above 8.0 result in an overblown image.
sun_energy_range = [4.5, 6.0]

# Sun spread angle randomness in degrees. Low/high bounds.
# Sun spread angle is how much the shadow diffuses based on the distance from the shadercaster.
# Lower values result in sharper shadows.
sun_spread_angle_range_degrees = [0.25, 1.0]

# Random camera offset from -value to value.
# For reference, an unmodified jigsaw piece will have a width and height of 2.
camera_location_random = 0.25

# Random rotation of the camera in XYZ between -value and value in degrees.
camera_rotation_random = 2.5

# Random camera focal length in mm between min and max value.
# Standard phones have a focal length between 24.0mm and 28.0mm.
# https://thesmartphonephotographer.com/smartphone-camera-focal-length/
camera_lens = [24.0, 28.0]

# Floor scale between min and max.
# Has the effect of changing the size of the background texture.
# Lower values may result in the edges of the floor plane being visible.
floor_scale_range = [0.75, 1.5]

# JIGSAW PIECE RANDOM LIMITS
# ==========================
# Allowed sizes of the image texture on the jigsaw piece.
# Larger values result in the image being larger on the piece.
# E.g. 0.05 results in each piece having 5% of the total image.
piece_image_scale_range = [0.05, 0.15]

# Piece connector (ins and outs) scale between min and max.
# Values too large or small will cause vertex errors!
piece_end_scale_range = [0.75, 1.25]

# Adjusts the position of all warp modifiers between -value and value.
# Larger values result in more extreme and often unrealistic pieces.
# Smaller values result in more generic pieces.
piece_warp_location_randomness = 0.1

# Same as above, but for warp scale instead of position.
# This mainly effects the connectors rather than the corners.
# Largers values give more extreme connector size variation, etc...
piece_warp_scale_randomness = 0.1

# Chance for a side NOT to be an edge (between 0 and 1)
piece_type_cutoff_edge = 0.9

# If a side is not an edge, this is the chance for it to be an in or out connector.
# Larger values favour inward connectors.
piece_type_cutoff_inward = 0.5

# Thickness of the jigsaw piece in units between min and max.
piece_solidify_thickness_range = [0.15, 0.35]

# Thickness of the jigsaw piece's bevel between min and max.
# Larger values result in more distortion around the edges of the piece.
piece_bevel_thickness_range = [0.05, 0.1]

# Piece specular range between min and max.
# Adjusts the specular value of the jigsaw piece's material.
# Largers values make the piece more glossy (shine spot from the light source.)
# Lower values make it more matte.
piece_specular_range = [0.05, 0.2]

# END RANDOM LIMITS

# Global config options
enable_camera_randomness = True
enable_lighting = True
enable_base_image_copy = False

# Randomise the environment
def random_env():
    if enable_lighting:
        # Sun rotation/angle
        sun.rotation_euler.x = math.radians(random.uniform(-sun_rotation_limit_degrees, sun_rotation_limit_degrees))
        sun.rotation_euler.y = math.radians(random.uniform(-sun_rotation_limit_degrees, sun_rotation_limit_degrees))
        sun.rotation_euler.z = math.radians(random.uniform(-sun_rotation_limit_degrees, sun_rotation_limit_degrees))

        # Sun energy and sun SPREAD angle (not direction, it controls shadow sharpness)
        sun.data.energy = random.uniform(sun_energy_range[0], sun_energy_range[1])
        sun.data.angle = random.uniform(sun_spread_angle_range_degrees[0], sun_spread_angle_range_degrees[1])

        # Random light tint to simulate different lighting conditions
        # Generate 3 random numbers as RGB and average them with the light's default color (white)
        light_random_tint = [random.random(), random.random(), random.random()]
        for i in range(0, 3):
            sun.data.color[i] = (sun.data.color[i] + light_random_tint[i]) / 2

    if enable_camera_randomness:
        # Random location of camera
        camera.location.x += random.uniform(-camera_location_random, camera_location_random)
        camera.location.y += random.uniform(-camera_location_random, camera_location_random)
        camera.location.z += random.uniform(-camera_location_random, camera_location_random)

        # Random rotation of camera
        camera.rotation_euler.x += math.radians(random.uniform(-camera_rotation_random, camera_rotation_random))
        camera.rotation_euler.y += math.radians(random.uniform(-camera_rotation_random, camera_rotation_random))
        camera.rotation_euler.z += math.radians(random.uniform(-camera_rotation_random, camera_rotation_random))

        # Random camera focal length
        camera.data.lens = random.uniform(camera_lens[0], camera_lens[1])

    # Move to randomise the floor
    random_floor()

# Randomise the floor scale, rotation, and texture
def random_floor():
    # Choose a random image...
    random_index = random.randrange(0, len(input_floor_images))

    # ...and apply each component to the floor
    apply_to_floor(random_index, "color")
    apply_to_floor(random_index, "displacement")
    apply_to_floor(random_index, "metallic")
    apply_to_floor(random_index, "normal")
    apply_to_floor(random_index, "roughness")

    # Randomise the floor rotation and scale
    floor.rotation_euler.z = math.radians(random.uniform(0, 360))
    floor_scale = random.uniform(floor_scale_range[0], floor_scale_range[1])
    floor.scale = [floor_scale, floor_scale, 1]

# Apply a 'property' to the floor texture
# Property refers to "color", "normal", "roughness", etc...
def apply_to_floor(index, property):
    if input_floor_images[index].get(property):
        bpy.data.images[property].filepath = input_floor_images[index][property]
    else:
        # If the texture has no such property, use a fallback
        bpy.data.images[property].filepath = os.path.join(fallback_material_path, property)
    
    # Reload the image from the updated filepath
    bpy.data.images[property].reload()

# Randomise global variables
def randomise():
    global piece_overall_scale, piece_end_scale

    piece_overall_scale = random.uniform(piece_image_scale_range[0], piece_image_scale_range[1])
    piece_end_scale = random.uniform(piece_end_scale_range[0], piece_end_scale_range[1])

# Generate the whole piece from the piece section
def generate_piece(index):
    global modifier_tos
    global modifier_froms
    global pieces

    # Randomise globals...
    randomise()

    # Add a new weld modifier and set the threshold
    # This will remove overlapping vertices when the mesh is duplicated
    modifier = piece.modifiers.new(name="Weld", type="WELD")
    modifier.merge_threshold = 0.005

    # Loop to create the 'empties' and associated warp modifiers to randomise the piece
    for i in range(0, 8):
        # Create to new empties, one as the warp original location, one as the warp target location
        modifier_froms.append(bpy.data.objects.new("empty", None))
        modifier_tos.append(bpy.data.objects.new("empty", None))

        # Place the objects in the world
        bpy.context.collection.objects.link(modifier_froms[i])
        bpy.context.collection.objects.link(modifier_tos[i])
        
        # Set the 'original location' empty's position to the position as declared in the modifier_positions list.
        modifier_froms[i].location = modifier_positions[i]

        # Set the 'target location' empties position to a random location relative to the 'original'
        modifier_tos[i].location.x = modifier_positions[i][0] + (random.uniform(-piece_warp_location_randomness, piece_warp_location_randomness))
        modifier_tos[i].location.y = modifier_positions[i][1] + (random.uniform(-piece_warp_location_randomness, piece_warp_location_randomness))
        
        # Also randomise scale
        modifier_tos[i].scale.x = piece_end_scale + (random.uniform(-piece_warp_scale_randomness, piece_warp_scale_randomness))
        modifier_tos[i].scale.y = piece_end_scale + (random.uniform(-piece_warp_scale_randomness, piece_warp_scale_randomness))
        
        # Create a warp modifier, configure the settings, and add it to the piece
        modifier = piece.modifiers.new(name="Warp", type="WARP")
        modifier.falloff_radius = 1.0
        modifier.use_volume_preserve = True
        modifier.object_from = modifier_froms[i]
        modifier.object_to = modifier_tos[i]

    # Duplicate the piece section four times to create a full piece.
    for i in range(0, 4):
        # Create a copy of the object and place it in the list
        new_piece = piece.copy()
        pieces.append(new_piece)
        
        # Copy over the object data
        new_piece.data = piece.data.copy()

        # Set the rotation
        new_piece.rotation_euler[2] = math.radians(i * 90)
        
        # Create a mask modifier that will show and hide different vertex groups
        modifier = new_piece.modifiers.new(name="Mask " + str(i), type="MASK")
        modifier.use_smooth = True

        # Choose the type of piece side
        # E.g. Inward connector, outward connector, or edge.
        type_index = random.random()

        # First check if it isn't an edge...
        if (type_index < piece_type_cutoff_edge):
            type_index = random.random()
            # Then check if inward or outward
            if (type_index < piece_type_cutoff_inward):
                type_index = "Inward"
            else:
                type_index = "Outward"
        else:
            type_index = "Edge"

        # Set the result in the mask modifier
        modifier.vertex_group = type_index
        
        # Add the piece section to the scene
        bpy.context.collection.objects.link(new_piece)

        # Set the piece section as active and apply the mask modifier
        # Needs to be applied otherwise the name will conflict with modifiers from other pieces when joined.
        bpy.context.view_layer.objects.active = new_piece
        bpy.ops.object.modifier_apply(modifier="Mask " + str(i))
        
        # Set the piece as selected (needed for 'join' later)
        new_piece.select_set(True)

    # Hide the original refernce piece section.
    piece.hide_set(True)
    piece.hide_render = True

    # Join all the piece sections into one mesh/object
    bpy.context.view_layer.objects.active = pieces[0]
    bpy.ops.object.join()

    # Apply all modifiers
    for modifier in bpy.context.view_layer.objects.active.modifiers:
        bpy.ops.object.modifier_apply(modifier=modifier.name)

    # Recalculate the origin (where 0,0,0 is) based on the center of mass of the randomised piece
    bpy.ops.object.origin_set(type="ORIGIN_CENTER_OF_MASS")
    # Center the object
    bpy.context.view_layer.objects.active.location = [0,0,0]

    # Calculate the UV data for the piece and output it to a file
    output_uv_data(index)

    # Create a solidify modifier to give the piece some thickness
    modifier = bpy.context.view_layer.objects.active.modifiers.new(name="Solidify", type="SOLIDIFY")
    modifier.thickness = random.uniform(piece_solidify_thickness_range[0], piece_solidify_thickness_range[1])

    # Create a subdivision surface modifier to increase the resolution of the mesh, and make it rounded.
    modifier = bpy.context.view_layer.objects.active.modifiers.new(name="Subdivide", type="SUBSURF")
    modifier.levels = 3
    modifier.render_levels = 3

    # Create a bevel to emulate the die-cut nature of pieces.
    modifier = bpy.context.view_layer.objects.active.modifiers.new(name="Bevel", type="BEVEL")
    modifier.segments = 4
    modifier.width = random.uniform(piece_bevel_thickness_range[0], piece_bevel_thickness_range[1])

    # Give the piece a random specular value (emulate the glossy finish)
    piece.material_slots[0].material.node_tree.nodes["Principled BSDF"].inputs["Specular"].default_value = random.uniform(piece_specular_range[0], piece_specular_range[1])

# Generate the UV coords for the piece and output
def output_uv_data(index):
    global current_csv_output

    # Add base image to CSV
    current_csv_output += current_image_filename + ","
    
    # Add the index to the CSV output
    current_csv_output += str(index) + ","

    # Activate edit mode so we can unwrap the mesh
    bpy.context.view_layer.objects.active.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    # Select all vertices
    bpy.ops.mesh.select_all(action="SELECT")

    # If the mesh has never been unwrapped, create a new layer to place the vertices on.
    if len(bpy.context.view_layer.objects.active.data.uv_layers) == 0:
        bpy.context.view_layer.objects.active.data.uv_layers.new()

    # Unwrap the UV using Blender's default unwrap method and return to object view
    bpy.ops.uv.unwrap(method="ANGLE_BASED", fill_holes=True, correct_aspect=True, use_subsurf_data=False, margin=0.001)
    bpy.ops.object.mode_set(mode="OBJECT")

    # Get every corner vertex's XY coord.
    # A corner vertex is a vertex that belongs to the vertex group 'Corner'
    # Note: At this point, we are still operating on a low resolution (low number of vertices) jigsaw piece
    corner_xys = []
    for vertex in bpy.context.object.data.vertices:
        for group in vertex.groups:
            if group.group == bpy.context.object.vertex_groups["Corner"].index:
                corner_xys.append(vertex.co.xy)

    # Move back to edit mode and create a new bmesh which gives us easier access to UV information
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(bpy.context.active_object.data)

    # Get the UV layer (or create one if it doesn't exist)
    uv_layer = bm.loops.layers.uv.verify()

    # Squish to correct aspect ratio
    # Currently, the UV does not respect the aspect ratio of the base image
    for face in bm.faces:
        for loop in face.loops:
            # If wider than tall, squish on the Y axis
            if bpy.data.images["baseimage"].size[0] < bpy.data.images["baseimage"].size[1]:
                aspect_ratio = bpy.data.images["baseimage"].size[0] / bpy.data.images["baseimage"].size[1]
                loop[uv_layer].uv.y *= aspect_ratio
            else:
                # Else, squish on X axis
                aspect_ratio = bpy.data.images["baseimage"].size[1] / bpy.data.images["baseimage"].size[0]
                loop[uv_layer].uv.x *= aspect_ratio

            # Apply generated scale for piece
            loop[uv_layer].uv.x *= piece_overall_scale
            loop[uv_layer].uv.y *= piece_overall_scale

    # Give the piece's image a random rotation
    bmesh.ops.rotate(bm, cent=[0.5, 0.5, 0.5], matrix=mathutils.Matrix.Rotation(math.radians(random.random() * 360), 3, "Z"))

    # At this point, the UV is still in the center of the base
    # Create an AABB (axis-aligned bounding box) for calculating maximum UV movement
    uv_min_x = 9999 # UV coords are between 0 and 1 anyway
    uv_min_y = 9999
    uv_max_x = -9999
    uv_max_y = -9999

    # For each vertex...
    for face in bm.faces:
        for loop in face.loops:
            # ...check if we need to update any mins or maxes
            if uv_min_x > loop[uv_layer].uv.x:
                uv_min_x = loop[uv_layer].uv.x
            if uv_min_y > loop[uv_layer].uv.y:
                uv_min_y = loop[uv_layer].uv.y
            if uv_max_x < loop[uv_layer].uv.x:
                uv_max_x = loop[uv_layer].uv.x
            if uv_max_y < loop[uv_layer].uv.y:
                uv_max_y = loop[uv_layer].uv.y
    
    # Get the size of the AABB
    uv_x_size = (uv_max_x - uv_min_x)
    uv_y_size = (uv_max_y - uv_min_y)

    # Calculate the random offset with a maximum of 1.0 minus the size.
    # This ensures that the UV will never exceed 1.0.
    uv_offset_x = random.uniform(0.0, 1.0 - uv_x_size)
    uv_offset_y = random.uniform(0.0, 1.0 - uv_y_size)

    # Currently found corners
    corner_count = 0

    # Move the whole UV to the randomised offset and record the corner UV positions
    for face in bm.faces:
        for loop in face.loops:
            # Reset to 0, 0
            loop[uv_layer].uv.x -= uv_min_x
            loop[uv_layer].uv.y -= uv_min_y

            # Add random offset
            loop[uv_layer].uv.x += uv_offset_x
            loop[uv_layer].uv.y += uv_offset_y
            
            # If the UV is a corner...
            if loop.vert.co.xy in corner_xys:
                # Remove it from the list to prevent overlapping corners where the duplicated pieces meet.
                corner_xys.remove(loop.vert.co.xy)

                # Log it to the CSV output
                corner_count += 1
                current_csv_output += str(loop[uv_layer].uv.x) + ","
                
                # Add a new line at the end if all corners have been found
                if corner_count != 4:
                    current_csv_output += str(loop[uv_layer].uv.y) + ","
                else:
                    current_csv_output += str(loop[uv_layer].uv.y) + "\n"

    # Applies the UV that was editied in the bmesh back to the original object
    bmesh.update_edit_mesh(bpy.context.active_object.data)

    # Return to object mode
    bpy.ops.object.mode_set(mode="OBJECT")

# Returns the scene/collection to original settings so the script can repeat correctly
def clean_up():
    # Deselect all objects and select only objects we need to delete
    bpy.ops.object.select_all(action="DESELECT")
    for obj in modifier_froms:
        obj.select_set(True)

    for obj in modifier_tos:
        obj.select_set(True)

    # This stores the main (joined) jigsaw piece
    pieces[0].select_set(True)

    # Delete the objects
    bpy.ops.object.delete()

    # Reset randomised values to defaults
    floor.rotation_euler.z = 0
    floor.scale = [1,1,1]
    camera.location = [0,0,3]
    camera.rotation_euler = [0,0,0]
    camera.data.lens = 25.0
    sun.rotation_euler = [0,0,0]
    sun.data.color = [1,1,1]
    sun.data.energy = 5
    sun.data.angle = 0.526

    # Unhide the original piece
    piece.hide_set(False)
    piece.hide_render = False

    # Remove all modifiers from the original piece
    piece.modifiers.clear()

    # Reset specular
    mat = piece.material_slots[0].material.node_tree.nodes["Principled BSDF"].inputs["Specular"].default_value = 0.0

    # Clear the lists
    modifier_tos.clear()
    modifier_froms.clear()
    pieces.clear()

# Check if a texture exists for a given property and return it inside a dictionary
def floor_get_from_path(path, property, dict):
    new_dict = dict

    # Check for both JPGs and PNGs.
    if (os.path.exists(os.path.join(path, property + ".jpg"))):
        new_dict[property] = os.path.join(path, property + ".jpg")
    if (os.path.exists(os.path.join(path, property + ".png"))):
        new_dict[property] = os.path.join(path, property + ".png")

    return new_dict

# Renders the scene to a file
def render(index):
    # Set the filepath and render a single frame
    bpy.context.scene.render.filepath = os.path.join(current_output_path, str(index) + ".png")
    bpy.ops.render.render(write_still = True)

# Write corner output to CSV
def write_csv():
    # Create the associated output file
    file = open(os.path.join(current_output_path, "data.csv"), "w")
    
    # Write headers
    file.write("base_path,piece_id,corner_1_x,corner_1_y,corner_2_x,corner_2_y,corner_3_x,corner_3_y,corner_4_x,corner_4_y\n")
    
    # Write piece data...
    file.write(current_csv_output)
    
    # Close file.
    file.close()

# User input common config options
def user_configure():
    global enable_lighting, enable_camera_randomness

    # Query using lighting
    print("Use lighting? (y/n)")
    enable_lighting = True if str(input()).lower().startswith("y") else False

    # Remove lighting if needed
    if not enable_lighting:
        sun.hide_set(True)
        sun.hide_render = True
        
        # Adjust exposure for no lighting
        bpy.context.scene.view_settings.exposure = 4.5
        
        # Disable compositing for a raw image
        bpy.context.scene.use_nodes = False

    # Query random camera
    print("Use random camera? (y/n)")
    enable_camera_randomness = True if str(input()).lower().startswith("y") else False

# Ready output variables
def ready_output():
    global current_output_path, current_csv_output, current_image_filename
    current_output_path = ""
    current_csv_output = ""
    current_image_filename = ""

# Apply the base image to the piece
def set_base_image(base_image_path):
    global current_image_filename

    # Set image filename for CSV
    current_image_filename = os.path.basename(base_image_path)

    # Set the base image
    bpy.data.images["baseimage"].filepath = base_image_path
    bpy.data.images["baseimage"].reload()

# Begin execution here...
# Create the output path if it doesn't exist
if not os.path.exists(output_path):
    os.makedirs(output_path)

# Get all input images as paths
input_base_images = []
for image in os.listdir(input_base_images_path):
    if os.path.isdir(os.path.join(input_base_images_path, image)):
        continue
    input_base_images.append(os.path.join(input_base_images_path, image))

# Get all floor texture files as paths inside dictionaries
input_floor_images = []
for image_index in os.listdir(input_floor_images_path):
    # Do not process the fallback as a proper image
    if image_index == "fallback":
        continue

    # Get the path to the current floor folder
    floor_path_full = os.path.join(input_floor_images_path, image_index)

    # Populate the dictionary with valid texture properties
    temp_dict = {}
    temp_dict = floor_get_from_path(floor_path_full, "color", temp_dict)
    temp_dict = floor_get_from_path(floor_path_full, "displacement", temp_dict)
    temp_dict = floor_get_from_path(floor_path_full, "metallic", temp_dict)
    temp_dict = floor_get_from_path(floor_path_full, "normal", temp_dict)
    temp_dict = floor_get_from_path(floor_path_full, "roughness", temp_dict)

    # Save the dictionary to a global list
    input_floor_images.append(temp_dict)

# Begin user input
print("Select generation mode:\n 1.\tGenerate X images per base\n 2.\tGenerate X images using random bases")
generation_mode = int(input())

if generation_mode == 1:
    print("Images per base: (there are " + str(len(input_base_images)) + " bases)")
    images_per_base = int(input())

    user_configure()

    print("Copy base image to output? (y/n)")
    enable_base_image_copy = True if str(input()).lower().startswith("y") else False

    ready_output()

    # For-loop to coordinate the process
    for base_index in range(0, len(input_base_images)):
        # Reset CSV output
        current_csv_output = ""

        set_base_image(input_base_images[base_index])

        # Set the correct output path for renders and CSVs
        current_output_path = os.path.join(output_path, str(base_index))

        # Make it if it doesn't exist
        if not os.path.exists(current_output_path):
            os.makedirs(current_output_path)

        # Copy the base file to the output directory with an appropriate name
        if enable_base_image_copy:
            shutil.copyfile(input_base_images[base_index], os.path.join(current_output_path, "base.jpg"))

        # Begin generation loop...
        for count in range(0, images_per_base):
            # Randomise...
            random_env()

            # Then generate the piece...
            generate_piece(count)

            # Then render...
            render(count)

            # Then clean up...
            clean_up()
        
        # Write CSV
        write_csv()
    
elif generation_mode == 2:
    print("Total number of images to generate:")
    images_total = int(input())

    user_configure()
    ready_output()

    # Set the correct output path for renders and CSVs
    current_output_path = output_path

    # Make it if it doesn't exist
    if not os.path.exists(current_output_path):
        os.makedirs(current_output_path)

    # For-loop to coordinate the process
    for index in range(images_total):
        # Choose random base image
        random_image = random.choice(input_base_images)
        set_base_image(random_image)

        # Randomise...
        random_env()

        # Then generate the piece...
        generate_piece(index)

        # Then render...
        render(index)

        # Then clean up...
        clean_up()
        
    # Write CSV
    write_csv()
