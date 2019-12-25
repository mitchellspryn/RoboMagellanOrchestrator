import airsim
import airsim.airsim_types as at

def get_ground(x, y, client):
    position = at.Vector3r(x_val = x, y_val = y, z_val = 10000)
    direction = at.Vector3r(x_val = 0, y_val = 0, z_val = -20000)
    through_blocking = True
    persist_seconds = 0
    reference_frame_link = ''

    request = at.RayCastRequest(position, direction, reference_frame_link, through_blocking, persist_seconds)
    
    response = client.simRayCast(request)

    ground_hit = None
    ground_hit_idx = None
    for i in range(0, len(response['hits']), 1):
        hit = response['hits'][i]
        actor_name = hit['collided_actor_name'].lower()

        # Do not allow spawns that are under water
        if ('water' in actor_name):
            return (None, None)

        if ('landscape' in actor_name or 'ground' in actor_name):
            ground_hit = hit
            ground_hit_idx = i
            break

    if (ground_hit is None):
        return (None, None)

    z_coord = ground_hit['hit_point']['z_val']
    normal = at.Vector3r(x_val = ground_hit['hit_normal']['x_val'], y_val = ground_hit['hit_normal']['y_val'], z_val = ground_hit['hit_normal']['z_val'])

    return (z_coord, normal)
