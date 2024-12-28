#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main() {
    system(".\\python\\scripts\\pip.exe uninstall pyqt6 frenpy && .\\python\\scripts\\pip.exe install pyqt6 frenpy");
    char command[256];
    strcpy(command, ".\\python\\python.exe .\\scripts\\frenpy_ide.py");
    system(command);

    return 0;
}
