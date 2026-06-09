import ctypes
from OpenGL.GL import *

class Mesh:
    def __init__(self, vertices, indices):
        self.index_count = len(indices)
        if not vertices or not indices:
            self.vao = self.vbo = self.ebo = None
            return

        vert = (ctypes.c_float * len(vertices))(*vertices)
        idx  = (ctypes.c_uint  * len(indices))(*indices)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(vert), vert, GL_STATIC_DRAW)

        self.ebo = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, ctypes.sizeof(idx), idx, GL_STATIC_DRAW)

        stride = 8 * 4
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(3 * 4))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(6 * 4))
        glEnableVertexAttribArray(2)

        glBindVertexArray(0)

    def draw(self):
        if self.vao is None:
            return
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, self.index_count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)

    def delete(self):
        if self.vao is not None:
            glDeleteVertexArrays(1, [self.vao])
            glDeleteBuffers(1, [self.vbo])
            glDeleteBuffers(1, [self.ebo])


def load_obj(path, uv_override=None):
    positions, normals, uvs = [], [], []
    verts_out, idx_out = [], []
    vtx_map = {}
    next_idx = 0
    uv_ctr = 0

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.strip().split()
            if not parts:
                continue
            tag = parts[0]
            if tag == "v":
                positions.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif tag == "vn":
                normals.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif tag == "vt":
                if uv_override is None:
                    uvs.append((float(parts[1]), float(parts[2])))
            elif tag == "f":
                face = []
                for tok in parts[1:]:
                    t = tok.split("/")
                    pi = int(t[0]) - 1
                    ti = int(t[1]) - 1 if len(t) > 1 and t[1] else -1
                    ni = int(t[2]) - 1 if len(t) > 2 and t[2] else -1
                    px, py, pz = positions[pi]
                    nx, ny, nz = normals[ni] if ni >= 0 else (0.0, 1.0, 0.0)
                    if uv_override is not None:
                        u, v = uv_override[uv_ctr % len(uv_override)]
                        uv_ctr += 1
                        # cada face-vértice gera entrada única (mapeamento posicional)
                        vert_idx = len(verts_out) // 8
                        verts_out.extend([px, py, pz, nx, ny, nz, u, v])
                        face.append(vert_idx)
                    else:
                        key = (pi, ni, ti)
                        if key not in vtx_map:
                            u, v = uvs[ti] if ti >= 0 else (0.0, 0.0)
                            verts_out.extend([px, py, pz, nx, ny, nz, u, v])
                            vtx_map[key] = next_idx
                            next_idx += 1
                        face.append(vtx_map[key])
                # triangulação em fan (cobre quads e n-gons do Blender)
                for i in range(1, len(face) - 1):
                    idx_out.extend([face[0], face[i], face[i + 1]])

    return Mesh(verts_out, idx_out)
