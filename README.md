# opencv_qt
1.You must run it as root because the code utillizes raw sockets for transmission  
2.Convert the raw socket send in Python to C.  
3.Steps to compile and include raw socket.so  
gcc -c -o raw_socket.o raw_socket.c -fPIC  
gcc -shared -o raw_socket.so raw_socket.o  
rm raw_socket.o  
