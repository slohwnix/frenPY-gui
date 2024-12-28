#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main() {
    system(".\\python\\python.exe .\\scripts\\update.py && .\\python\\scripts\\pip.exe install pyqt6 frenpy requests --upgrade");
    char command[256];
    strcpy(command, ".\\python\\python.exe .\\scripts\\frenpy_ide.py");
    system(command);

    return 0;
}
