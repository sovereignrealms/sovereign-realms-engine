#version 330 core

#define X_COORDS_PER_TILE  8
#define Z_COORDS_PER_TILE  8

#define STATE_UNEXPLORED 0
#define STATE_IN_FOG     1
#define STATE_VISIBLE    2

in VertexToFrag {
    vec4 clip_space_pos;
    vec3 world_pos;
    vec2 uv;
    vec3 view_dir;
    vec3 light_dir;
}from_vertex;

out vec4 o_frag_color;

uniform float water_move_factor;

uniform usamplerBuffer visbuff;
uniform int visbuff_offset;

uniform ivec4 map_resolution;
uniform vec2 map_pos;

/*
 * x = chunk_r
 * y = chunk_c
 * z = tile_r
 * w = tile_c
 */
ivec4 tile_desc_at(vec3 ws_pos)
{
    int chunk_w = map_resolution.x;
    int chunk_h = map_resolution.y;
    int tile_w = map_resolution.z;
    int tile_h = map_resolution.w;

    int chunk_x_dist = tile_w * X_COORDS_PER_TILE;
    int chunk_z_dist = tile_h * Z_COORDS_PER_TILE;

    int chunk_r = int(abs(map_pos.y - ws_pos.z) / chunk_z_dist);
    int chunk_c = int(abs(map_pos.x - ws_pos.x) / chunk_x_dist);

    int chunk_base_x = int(map_pos.x - (chunk_c * chunk_x_dist));
    int chunk_base_z = int(map_pos.y + (chunk_r * chunk_z_dist));

    int tile_c = int(abs(chunk_base_x - ws_pos.x) / X_COORDS_PER_TILE);
    int tile_r = int(abs(chunk_base_z - ws_pos.z) / Z_COORDS_PER_TILE);

    return ivec4(
        clamp(chunk_r, 0, chunk_h - 1),
        clamp(chunk_c, 0, chunk_w - 1),
        clamp(tile_r, 0, tile_h - 1),
        clamp(tile_c, 0, tile_w - 1)
    );
}

int visbuff_idx(ivec4 td)
{
    int chunk_w = map_resolution.x;
    int tile_w = map_resolution.z;
    int tile_h = map_resolution.w;
    int tiles_per_chunk = tile_w * tile_h;

    return visbuff_offset + (td.x * tiles_per_chunk * chunk_w)
                          + (td.y * tiles_per_chunk)
                          + (td.z * tile_w)
                          + td.w;
}

float tint_factor(uint state)
{
    if(state == uint(STATE_UNEXPLORED))
        return 0.0;
    if(state == uint(STATE_IN_FOG))
        return 0.45;
    return 1.0;
}

void main()
{
    ivec4 td = tile_desc_at(from_vertex.world_pos);
    float fog_tint = tint_factor(texelFetch(visbuff, visbuff_idx(td)).r);

    if(fog_tint <= 0.0) {
        o_frag_color = vec4(0.0, 0.0, 0.0, 1.0);
        return;
    }

    float wave = 0.5 + 0.5 * sin((from_vertex.uv.x + water_move_factor * 4.0) * 7.0
                               + (from_vertex.uv.y - water_move_factor * 2.0) * 5.0);
    float fresnel = pow(1.0 - max(dot(normalize(from_vertex.view_dir), vec3(0.0, 1.0, 0.0)), 0.0), 2.0);

    vec3 deep = vec3(0.02, 0.17, 0.32);
    vec3 shallow = vec3(0.06, 0.34, 0.52);
    vec3 highlight = vec3(0.34, 0.55, 0.70);

    vec3 color = mix(deep, shallow, wave);
    color = mix(color, highlight, fresnel * 0.35);
    color *= fog_tint;

    float alpha = mix(0.68, 0.84, wave);
    o_frag_color = vec4(color, alpha);
}
