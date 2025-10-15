#include <stdio.h>

__attribute__((constructor))
static void init_stub(void) {
    fprintf(stderr, "[opengl-stub] Loaded software OpenGL compatibility shim.\n");
}

int glx_stub_placeholder(void) {
    return 0;
}
