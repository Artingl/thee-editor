#include <stdio.h>

void say_hello(const char *name)
{
    printf("Hello, %s!", name);
}

int main(void)
{
    printf("Hello world!\n");

    int test = 0;


    say_hello("Artem!");

    return 0;
}








