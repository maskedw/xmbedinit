#include "mbed.h"

DigitalOut myled(LED1);
Serial pc(USBTX, USBRX);

int main()
{
    pc.printf("{% include 'generated_by.txt' %}");
    while(1)
    {
        myled = 1;
        wait(0.2);
        myled = 0;
        wait(0.2);
    }

    return 0;
}
