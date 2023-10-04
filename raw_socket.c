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

#define MAX_FRAME_SIZE 1477
#define MAX_DATA_LENGTH 1500

int raw_sock = -1;
struct sockaddr_ll socket_address;
struct ifreq ifr;

int set_raw_socket_init(const char *interface) {
    int ss = 0;
    struct sockaddr_ll sa;
    size_t if_name_len = 0;

    if_name_len = strlen(interface);

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

    if (bind(raw_sock, (const struct sockaddr *)&sa, sizeof(sa)) < 0) {
        perror("bind");
        close(raw_sock);
        return -1;
    }

    ss = setsockopt(raw_sock, SOL_SOCKET, SO_BINDTODEVICE, interface, strlen(interface));

    if (ss < 0) {
        perror("setsockopt");
        close(raw_sock);
        return -1;
    }

    return 1;
}

int send_raw_socket_packet(unsigned char *packet_data , int packet_sz) {
    socket_address.sll_ifindex = ifr.ifr_ifindex;
    socket_address.sll_halen = ETH_ALEN;
    memcpy(socket_address.sll_addr, packet_data + 6, 6);

    if (sendto(raw_sock, packet_data, packet_sz, 0, (struct sockaddr *)&socket_address, sizeof(struct sockaddr_ll)) < 0) {
        perror("sendto");
        return -1;
    }

    return 1;
}

int send_fmt_packet(unsigned char *data, int length) {
    unsigned char combined_data[MAX_DATA_LENGTH];
    int packet_sz;
    const uint8_t fmt_cmd[19] = {
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, // Destination Address
        0x00, 0x00, 0x00, 0x00, 0x00, 0x01, // Source Address
        0x00, 0x05,                         // Number of Data Byte
        0x10,                               // Flow Ctrl
                                            // DATA
        0x00, 0x00, 0x06, 0xA5,             // CRC
    };

    packet_sz = length + sizeof(fmt_cmd);

    if (packet_sz > MAX_DATA_LENGTH) {
        printf("Error:  Fmt data too long. Length: %d bytes\n", packet_sz);
        return -1;
    }

    memcpy(combined_data, fmt_cmd, 19);
    memcpy(combined_data + 19, data, length);

    if (send_raw_socket_packet(combined_data, packet_sz) == -1) {
        printf("Sending failed\n");
        return -1;
    }

    return 1;
}
/*********************************************
 *  Format Description:
 *  [FMT] - FPGA Vendor-defined packet format
 *  [FRAME ID] - Frame Identifier
 *  [SEQ ID] - Sequence Identifier
 *  [RGB FRAME] - RGB Frame Data
 **********************************************/
int send_rgb_frame_with_raw_socket(const unsigned char *rgb_frame, int frame_sz, unsigned int frame_id) {
    unsigned int i = 0; 
    unsigned char frame_id_bytes[2];
    int segment_length;
    unsigned char seq_id_bytes[2];
    unsigned char raw_socket_packet[MAX_DATA_LENGTH];
    unsigned int seq_id = 0;
    int data_length;

    if (frame_id > 0xffff) {
        printf("Error: frame_id is out of range (0xffff)\n");
        return -1;
    }

    frame_id_bytes[0] = (frame_id >> 8) & 0xFF;
    frame_id_bytes[1] = frame_id & 0xFF;

    while (i < frame_sz) {
        segment_length = (frame_sz - i > MAX_FRAME_SIZE) ? MAX_FRAME_SIZE : frame_sz - i;

        seq_id_bytes[0] = (seq_id >> 8) & 0xFF;
        seq_id_bytes[1] = seq_id & 0xFF;

        data_length = 2 + 2 + segment_length;

        if (data_length > MAX_DATA_LENGTH) {
            printf("Error:  TX frame data too long. Length: %d bytes\n", data_length);
            return -1;
        }

        memcpy(raw_socket_packet, frame_id_bytes, 2);
        memcpy(raw_socket_packet + 2, seq_id_bytes, 2);
        memcpy(raw_socket_packet + 4, rgb_frame + i, segment_length);

        send_fmt_packet(raw_socket_packet, data_length);
        seq_id++;
        i += MAX_FRAME_SIZE;
    }

    return 1;
}

