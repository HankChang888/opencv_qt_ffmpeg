#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <netinet/ip.h>
#include <netinet/udp.h>
#include <arpa/inet.h>
#include <string.h>
#include <linux/if_packet.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <net/if.h>
#include <netinet/ether.h>
#include <pthread.h>
#include <unistd.h>

int raw_sock = -1;
char g_str_raw_socket_interface[32];
struct sockaddr_ll socket_address;
struct ifreq ifr;

int set_raw_socket_init(const char *interface)
{
    int ss = 0;
    struct sockaddr_ll sa;

    int iflen = 0;
    size_t if_name_len = 0;

    iflen = strlen(interface);

    if (iflen > sizeof(g_str_raw_socket_interface))
        return -1;

    strcpy(g_str_raw_socket_interface, interface);

    if_name_len = iflen;

    if (raw_sock != -1)
        close(raw_sock);

    raw_sock = socket(PF_PACKET, SOCK_RAW, htons(ETH_P_ALL));

    if (raw_sock < 0) {
        fprintf(stderr, "Error: Can't open socket.\n");
        return -1;
    }

    if (if_name_len < sizeof(ifr.ifr_name)) {
        memcpy(ifr.ifr_name, interface, if_name_len);
        ifr.ifr_name[if_name_len] = 0;
    } else {
        close(raw_sock);
        return -1;
    }

    ioctl(raw_sock, SIOCGIFINDEX, &ifr);

    memset(&sa, 0, sizeof(sa));
    sa.sll_family = PF_PACKET;
    sa.sll_protocol = 0x0000;
    sa.sll_ifindex = ifr.ifr_ifindex;
    sa.sll_hatype = 0;
    sa.sll_pkttype = PACKET_HOST;

    bind(raw_sock, (const struct sockaddr *)&sa, sizeof(sa));
    ss = setsockopt(raw_sock, SOL_SOCKET, SO_BINDTODEVICE, interface, strlen(interface));

    if (ss < 0) {
        close(raw_sock);
        return -1;
    }

    return 1;
}

int send_raw_socket_packet(unsigned char *packet_data , int packet_sz)
{
    socket_address.sll_ifindex = ifr.ifr_ifindex;
    socket_address.sll_halen = ETH_ALEN;
    memcpy(socket_address.sll_addr, packet_data + 6, 6);

    if (sendto(raw_sock, packet_data, packet_sz, 0, (struct sockaddr *)&socket_address, sizeof(struct sockaddr_ll)) < 0) {
        printf("Send failed\n");
        return -1;
    }

    return 1;
}
