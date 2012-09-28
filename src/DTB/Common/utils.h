/**
 * Utility funtions.
 *
 * @author  alessandro.daducci@epfl.ch
 * @date, 08/03/2011
 */
#ifndef __UTILS_H__
#define __UTILS_H__

typedef struct {
	int	x, y, z;
} Vec3Di;

typedef struct {
	float	x, y, z;
} Vec3Df;


float ScalarProduct(const Vec3Df & v1, const Vec3Df & v2)
{
	return v1.x*v2.x + v1.y*v2.y + v1.z*v2.z;
}
float ScalarProduct(const Vec3Di & v1, const Vec3Di & v2)
{
	return v1.x*v2.x + v1.y*v2.y + v1.z*v2.z;
}

void Normalize(Vec3Df & v)
{
	float norm = sqrt(v.x*v.x + v.y*v.y + v.z*v.z);
	if ( norm > 0 ) {
		v.x = v.x / norm;
		v.y = v.y / norm;
		v.z = v.z / norm;
	}
}

#endif
