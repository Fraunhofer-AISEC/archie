# Implementation of the differential fault attack for the M0 fault model
#
# For a description of this attack see:
# Dhiman Saha, Debdeep Mukhopadhyay and Dipanwita Roy Chowdhury
# A Diagonal Fault Attack on the Advanced Encryption Standard.
# IACR Cryptology ePrint Archive, 581, 2009.
#
# input: faulty cipher texts and correct cipher text after the 10th round
# output: key set for round 10

#fmt: off
# inverse s-box
invSBox = (
    0x52, 0x09, 0x6a, 0xd5, 0x30, 0x36, 0xa5, 0x38, 0xbf, 0x40, 0xa3, 0x9e, 0x81, 0xf3, 0xd7, 0xfb,
    0x7c, 0xe3, 0x39, 0x82, 0x9b, 0x2f, 0xff, 0x87, 0x34, 0x8e, 0x43, 0x44, 0xc4, 0xde, 0xe9, 0xcb,
    0x54, 0x7b, 0x94, 0x32, 0xa6, 0xc2, 0x23, 0x3d, 0xee, 0x4c, 0x95, 0x0b, 0x42, 0xfa, 0xc3, 0x4e,
    0x08, 0x2e, 0xa1, 0x66, 0x28, 0xd9, 0x24, 0xb2, 0x76, 0x5b, 0xa2, 0x49, 0x6d, 0x8b, 0xd1, 0x25,
    0x72, 0xf8, 0xf6, 0x64, 0x86, 0x68, 0x98, 0x16, 0xd4, 0xa4, 0x5c, 0xcc, 0x5d, 0x65, 0xb6, 0x92,
    0x6c, 0x70, 0x48, 0x50, 0xfd, 0xed, 0xb9, 0xda, 0x5e, 0x15, 0x46, 0x57, 0xa7, 0x8d, 0x9d, 0x84,
    0x90, 0xd8, 0xab, 0x00, 0x8c, 0xbc, 0xd3, 0x0a, 0xf7, 0xe4, 0x58, 0x05, 0xb8, 0xb3, 0x45, 0x06,
    0xd0, 0x2c, 0x1e, 0x8f, 0xca, 0x3f, 0x0f, 0x02, 0xc1, 0xaf, 0xbd, 0x03, 0x01, 0x13, 0x8a, 0x6b,
    0x3a, 0x91, 0x11, 0x41, 0x4f, 0x67, 0xdc, 0xea, 0x97, 0xf2, 0xcf, 0xce, 0xf0, 0xb4, 0xe6, 0x73,
    0x96, 0xac, 0x74, 0x22, 0xe7, 0xad, 0x35, 0x85, 0xe2, 0xf9, 0x37, 0xe8, 0x1c, 0x75, 0xdf, 0x6e,
    0x47, 0xf1, 0x1a, 0x71, 0x1d, 0x29, 0xc5, 0x89, 0x6f, 0xb7, 0x62, 0x0e, 0xaa, 0x18, 0xbe, 0x1b,
    0xfc, 0x56, 0x3e, 0x4b, 0xc6, 0xd2, 0x79, 0x20, 0x9a, 0xdb, 0xc0, 0xfe, 0x78, 0xcd, 0x5a, 0xf4,
    0x1f, 0xdd, 0xa8, 0x33, 0x88, 0x07, 0xc7, 0x31, 0xb1, 0x12, 0x10, 0x59, 0x27, 0x80, 0xec, 0x5f,
    0x60, 0x51, 0x7f, 0xa9, 0x19, 0xb5, 0x4a, 0x0d, 0x2d, 0xe5, 0x7a, 0x9f, 0x93, 0xc9, 0x9c, 0xef,
    0xa0, 0xe0, 0x3b, 0x4d, 0xae, 0x2a, 0xf5, 0xb0, 0xc8, 0xeb, 0xbb, 0x3c, 0x83, 0x53, 0x99, 0x61,
    0x17, 0x2b, 0x04, 0x7e, 0xba, 0x77, 0xd6, 0x26, 0xe1, 0x69, 0x14, 0x63, 0x55, 0x21, 0x0c, 0x7d
)

# exponential table: lookup table for l table addition result
e = (
    0x01, 0x03, 0x05, 0x0f, 0x11, 0x33, 0x55, 0xff, 0x1a, 0x2e, 0x72, 0x96, 0xa1, 0xf8, 0x13, 0x35,
    0x5f, 0xe1, 0x38, 0x48, 0xd8, 0x73, 0x95, 0xa4, 0xf7, 0x02, 0x06, 0x0a, 0x1e, 0x22, 0x66, 0xaa,
    0xe5, 0x34, 0x5c, 0xe4, 0x37, 0x59, 0xeb, 0x26, 0x6a, 0xbe, 0xd9, 0x70, 0x90, 0xab, 0xe6, 0x31,
    0x53, 0xf5, 0x04, 0x0c, 0x14, 0x3c, 0x44, 0xcc, 0x4f, 0xd1, 0x68, 0xb8, 0xd3, 0x6e, 0xb2, 0xcd,
    0x4c, 0xd4, 0x67, 0xa9, 0xe0, 0x3b, 0x4d, 0xd7, 0x62, 0xa6, 0xf1, 0x08, 0x18, 0x28, 0x78, 0x88,
    0x83, 0x9e, 0xb9, 0xd0, 0x6b, 0xbd, 0xdc, 0x7f, 0x81, 0x98, 0xb3, 0xce, 0x49, 0xdb, 0x76, 0x9a,
    0xb5, 0xc4, 0x57, 0xf9, 0x10, 0x30, 0x50, 0xf0, 0x0b, 0x1d, 0x27, 0x69, 0xbb, 0xd6, 0x61, 0xa3,
    0xfe, 0x19, 0x2b, 0x7d, 0x87, 0x92, 0xad, 0xec, 0x2f, 0x71, 0x93, 0xae, 0xe9, 0x20, 0x60, 0xa0,
    0xfb, 0x16, 0x3a, 0x4e, 0xd2, 0x6d, 0xb7, 0xc2, 0x5d, 0xe7, 0x32, 0x56, 0xfa, 0x15, 0x3f, 0x41,
    0xc3, 0x5e, 0xe2, 0x3d, 0x47, 0xc9, 0x40, 0xc0, 0x5b, 0xed, 0x2c, 0x74, 0x9c, 0xbf, 0xda, 0x75,
    0x9f, 0xba, 0xd5, 0x64, 0xac, 0xef, 0x2a, 0x7e, 0x82, 0x9d, 0xbc, 0xdf, 0x7a, 0x8e, 0x89, 0x80,
    0x9b, 0xb6, 0xc1, 0x58, 0xe8, 0x23, 0x65, 0xaf, 0xea, 0x25, 0x6f, 0xb1, 0xc8, 0x43, 0xc5, 0x54,
    0xfc, 0x1f, 0x21, 0x63, 0xa5, 0xf4, 0x07, 0x09, 0x1b, 0x2d, 0x77, 0x99, 0xb0, 0xcb, 0x46, 0xca,
    0x45, 0xcf, 0x4a, 0xde, 0x79, 0x8b, 0x86, 0x91, 0xa8, 0xe3, 0x3e, 0x42, 0xc6, 0x51, 0xf3, 0x0e,
    0x12, 0x36, 0x5a, 0xee, 0x29, 0x7b, 0x8d, 0x8c, 0x8f, 0x8a, 0x85, 0x94, 0xa7, 0xf2, 0x0d, 0x17,
    0x39, 0x4b, 0xdd, 0x7c, 0x84, 0x97, 0xa2, 0xfd, 0x1c, 0x24, 0x6c, 0xb4, 0xc7, 0x52, 0xf6, 0x01
)


# logarithmic table: lookup table for multiplication
# initial value -1 is a dummy value
l = (
    -1, 0x00, 0x19, 0x01, 0x32, 0x02, 0x1a, 0xc6, 0x4b, 0xc7, 0x1b, 0x68, 0x33, 0xee, 0xdf, 0x03,
    0x64, 0x04, 0xe0, 0x0e, 0x34, 0x8d, 0x81, 0xef, 0x4c, 0x71, 0x08, 0xc8, 0xf8, 0x69, 0x1c, 0xc1,
    0x7d, 0xc2, 0x1d, 0xb5, 0xf9, 0xb9, 0x27, 0x6a, 0x4d, 0xe4, 0xa6, 0x72, 0x9a, 0xc9, 0x09, 0x78,
    0x65, 0x2f, 0x8a, 0x05, 0x21, 0x0f, 0xe1, 0x24, 0x12, 0xf0, 0x82, 0x45, 0x35, 0x93, 0xda, 0x8e,
    0x96, 0x8f, 0xdb, 0xbd, 0x36, 0xd0, 0xce, 0x94, 0x13, 0x5C, 0xd2, 0xf1, 0x40, 0x46, 0x83, 0x38,
    0x66, 0xdd, 0xfd, 0x30, 0xbf, 0x06, 0x8b, 0x62, 0xb3, 0x25, 0xe2, 0x98, 0x22, 0x88, 0x91, 0x10,
    0x7e, 0x6e, 0x48, 0xc3, 0xa3, 0xb6, 0x1e, 0x42, 0x3a, 0x6b, 0x28, 0x54, 0xfa, 0x85, 0x3d, 0xba,
    0x2b, 0x79, 0x0a, 0x15, 0x9b, 0x9f, 0x5e, 0xca, 0x4e, 0xd4, 0xac, 0xe5, 0xf3, 0x73, 0xa7, 0x57,
    0xaf, 0x58, 0xa8, 0x50, 0xf4, 0xea, 0xd6, 0x74, 0x4f, 0xae, 0xe9, 0xd5, 0xe7, 0xe6, 0xad, 0xe8,
    0x2c, 0xd7, 0x75, 0x7a, 0xeb, 0x16, 0x0b, 0xf5, 0x59, 0xcb, 0x5f, 0xb0, 0x9c, 0xa9, 0x51, 0xa0,
    0x7f, 0x0c, 0xf6, 0x6f, 0x17, 0xc4, 0x49, 0xec, 0xd8, 0x43, 0x1f, 0x2d, 0xa4, 0x76, 0x7b, 0xb7,
    0xcc, 0xbb, 0x3e, 0x5a, 0xfb, 0x60, 0xb1, 0x86, 0x3b, 0x52, 0xa1, 0x6c, 0xaa, 0x55, 0x29, 0x9d,
    0x97, 0xb2, 0x87, 0x90, 0x61, 0xbe, 0xdc, 0xfc, 0xbc, 0x95, 0xcf, 0xcd, 0x37, 0x3f, 0x5b, 0xd1,
    0x53, 0x39, 0x84, 0x3c, 0x41, 0xa2, 0x6d, 0x47, 0x14, 0x2a, 0x9e, 0x5d, 0x56, 0xf2, 0xd3, 0xab,
    0x44, 0x11, 0x92, 0xd9, 0x23, 0x20, 0x2e, 0x89, 0xb4, 0x7c, 0xb8, 0x26, 0x77, 0x99, 0xe3, 0xa5,
    0x67, 0x4a, 0xed, 0xde, 0xc5, 0x31, 0xfe, 0x18, 0x0d, 0x63, 0x8c, 0x80, 0xc0, 0xf7, 0x70, 0x07
)
#fmt: on

def mult(a, b):
    # cases 0x00 and 0x01 are specific in terms of multiplication
    r = 0
    if a == 0 or b == 0:
        return 0
    elif a == 1:
        return b
    elif b == 1:
        return a
    else:
        r = l[a] + l[b]
        if r > 0xFF:
            return e[r - 0xFF]
        else:
            return e[r]


# equations for the M0 fault model (see section 5.2 in the above-mentioned publication)
def differentialFaultAttack(c, keyset, x):
    key = [0] * 16
    # obtain set for key bytes 0, 7, 10 and 13
    for k in range(0, 256):
        key[0] = k
        # print(k)
        for j in range(0, 256):
            key[13] = j
            f1 = invSBox[key[0] ^ x[0]] ^ invSBox[key[0] ^ c[0]]
            f2 = invSBox[key[13] ^ x[13]] ^ invSBox[key[13] ^ c[13]]
            if f1 == mult(2, f2):
                for i in range(0, 256):
                    key[10] = i
                    f3 = invSBox[key[10] ^ x[10]] ^ invSBox[key[10] ^ c[10]]
                    if f3 == f2:
                        for n in range(0, 256):
                            key[7] = n
                            f4 = invSBox[key[7] ^ x[7]] ^ invSBox[key[7] ^ c[7]]
                            if mult(3, f3) == f4:
                                keyset[0].append(key[0])
                                keyset[13].append(key[13])
                                keyset[10].append(key[10])
                                keyset[7].append(key[7])

    # obtain set for key bytes 3, 6, 9 and 12
    for k in range(0, 256):
        key[12] = k
        # print(k)
        for j in range(0, 256):
            key[6] = j
            f1 = invSBox[key[12] ^ x[12]] ^ invSBox[key[12] ^ c[12]]
            f2 = invSBox[key[6] ^ x[6]] ^ invSBox[key[6] ^ c[6]]
            if f1 == mult(3, f2):
                for i in range(0, 256):
                    key[9] = i
                    f3 = invSBox[key[9] ^ x[9]] ^ invSBox[key[9] ^ c[9]]
                    if f3 == mult(2, f2):
                        for n in range(0, 256):
                            key[3] = n
                            f4 = invSBox[key[3] ^ x[3]] ^ invSBox[key[3] ^ c[3]]
                            if f2 == f4:
                                keyset[12].append(key[12])
                                keyset[6].append(key[6])
                                keyset[9].append(key[9])
                                keyset[3].append(key[3])

    # obtain set for key bytes 2, 5, 8 and 15
    for k in range(0, 256):
        key[8] = k
        # print(k)
        for j in range(0, 256):
            key[5] = j
            f1 = invSBox[key[8] ^ x[8]] ^ invSBox[key[8] ^ c[8]]
            f2 = invSBox[key[5] ^ x[5]] ^ invSBox[key[5] ^ c[5]]
            if mult(3, f1) == f2:
                for i in range(0, 256):
                    key[2] = i
                    f3 = invSBox[key[2] ^ x[2]] ^ invSBox[key[2] ^ c[2]]
                    if f3 == mult(2, f1):
                        for n in range(0, 256):
                            key[15] = n
                            f4 = invSBox[key[15] ^ x[15]] ^ invSBox[key[15] ^ c[15]]
                            if f1 == f4:
                                keyset[8].append(key[8])
                                keyset[5].append(key[5])
                                keyset[2].append(key[2])
                                keyset[15].append(key[15])

    # obtain set for key bytes 1, 4, 11 and 14
    for k in range(0, 256):
        key[1] = k
        # print(k)
        for j in range(0, 256):
            key[4] = j
            f1 = invSBox[key[4] ^ x[4]] ^ invSBox[key[4] ^ c[4]]
            f2 = invSBox[key[1] ^ x[1]] ^ invSBox[key[1] ^ c[1]]
            if f1 == f2:
                for i in range(0, 256):
                    key[14] = i
                    f3 = invSBox[key[14] ^ x[14]] ^ invSBox[key[14] ^ c[14]]
                    if f3 == mult(3, f2):
                        for n in range(0, 256):
                            key[11] = n
                            f4 = invSBox[key[11] ^ x[11]] ^ invSBox[key[11] ^ c[11]]
                            if mult(2, f2) == f4:
                                keyset[1].append(key[1])
                                keyset[4].append(key[4])
                                keyset[14].append(key[14])
                                keyset[11].append(key[11])


if __name__ == "__main__":
    key = [0] * 16
    #fmt: off
    # original ciphertext
    x = (0x3a, 0xd7, 0x7b, 0xb4, 0x0d, 0x7a, 0x36, 0x60, 0xa8, 0x9e, 0xca, 0xf3, 0x24, 0x66, 0xef, 0x97)
    # faulty ciphertexts
    cipher = (0x54, 0x12, 0xc6, 0x2e, 0xbb, 0x33, 0x9d, 0xc4, 0x4f, 0x47, 0x76, 0x3b, 0xfc, 0x4a, 0xc2, 0xbe)
    cipher1 = (0x7e, 0x1e, 0x7e, 0x29, 0x64, 0x20, 0x2b, 0x66, 0xc1, 0x06, 0x5e, 0x88, 0x8b, 0x35, 0x82, 0xbb)
    cipher2 = (0xb8, 0x37, 0x22, 0x8d, 0x6e, 0xdf, 0x7a, 0x85, 0xf0, 0x6b, 0xf4, 0x7b, 0x45, 0xa9, 0x23, 0x5f)
    cipher3 = (0x2b, 0x1e, 0x1c, 0x92, 0x64, 0xc7, 0x4c, 0x46, 0xf9, 0x18, 0x6e, 0x88, 0xab, 0xdd, 0x82, 0x08)
    cipher4 = (0xcd, 0xf2, 0x07, 0x0e, 0xe6, 0x58, 0xc9, 0x4e, 0x2d, 0x32, 0xb0, 0xd5, 0x43, 0xc4, 0x90, 0x33)
    #fmt: on

    # cipher key sets
    keysetCipher = [[] for i in range(0, 16)]
    keysetCipher1 = [[] for i in range(0, 16)]
    keysetCipher2 = [[] for i in range(0, 16)]
    keysetCipher3 = [[] for i in range(0, 16)]
    keysetCipher4 = [[] for i in range(0, 16)]
    # test first ciphertext to obtain reduced keyset
    differentialFaultAttack(cipher, keysetCipher, x)

    # test second ciphertext to obtain reduced keyset
    differentialFaultAttack(cipher1, keysetCipher1, x)

    # test third ciphertext to obtain reduced keyset
    differentialFaultAttack(cipher2, keysetCipher2, x)

    # test fourth ciphertext to obtain reduced keyset
    differentialFaultAttack(cipher3, keysetCipher3, x)

    # test fourth ciphertext to obtain reduced keyset
    differentialFaultAttack(cipher4, keysetCipher4, x)

    # remove duplicates, sort lists and print intersection
    print("reduced key set of tenth round key")
    for i in range(0, 16):
        keysetCipher[i] = list(set(keysetCipher[i]))
        keysetCipher[i].sort()
        keysetCipher1[i] = list(set(keysetCipher1[i]))
        keysetCipher1[i].sort()
        keysetCipher2[i] = list(set(keysetCipher2[i]))
        keysetCipher2[i].sort()
        keysetCipher3[i] = list(set(keysetCipher3[i]))
        keysetCipher3[i].sort()
        keysetCipher4[i] = list(set(keysetCipher4[i]))
        keysetCipher4[i].sort()
        intersection = list(
            set(keysetCipher[i])
            & set(keysetCipher1[i])
            & set(keysetCipher2[i])
            & set(keysetCipher3[i])
            & set(keysetCipher4[i])
        )
        print([hex(c) for c in intersection])
