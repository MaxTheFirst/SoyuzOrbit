#ifndef VEC3_H
#define VEC3_H

class Vec3 {
public:
    double x, y, z;

    Vec3(double x = 0, double y = 0, double z = 0);

    Vec3 operator+(const Vec3& other) const;
    Vec3 operator-(const Vec3& other) const;
    Vec3 operator*(double scalar) const;
    double dot(const Vec3& other) const;
    Vec3 cross(const Vec3& other) const;
    double length() const;
    Vec3 normalize() const;
};

#endif // VEC3_H
