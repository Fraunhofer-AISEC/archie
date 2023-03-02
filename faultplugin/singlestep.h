/*
 *   Copyright 2021 Florian Andreas Hauschild
 *   Copyright (c) 2021 Fraunhofer AISEC
 *   Fraunhofer-Gesellschaft zur Foerderung der angewandten Forschung e.V.
 *
 *   Licensed under the Apache License, Version 2.0 (the "License");
 *   you may not use this file except in compliance with the License.
 *   You may obtain a copy of the License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 *   Unless required by applicable law or agreed to in writing, software
 *   distributed under the License is distributed on an "AS IS" BASIS,
 *   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *   See the License for the specific language governing permissions and
 *   limitations under the License.
 *
 *   This file contains the headers for managing singlestep mode inside
 */

#ifndef SINGLESTEP
#define SINGLESTEP

/**
 * init_singlestep_req
 *
 * Init singlestep module. This will initialise all needed variables
 */
void init_singlestep_req(void);

/**
 * check_singlestep
 *
 * Check weather singlestepping should be enabled or not. It will disable singlestep if no requests are open. If requests are open it will force qemu into singlestep.
 */
void check_singlestep(void);

/**
 * add_singlestep_req
 *
 * Increase counter for requested singlesteps. This function should be called, if singlestep should be enabled. It will internally call check_singlestep
 */
void add_singlestep_req(void);

/**
 * rem_singlestep_req
 *
 * decrease counter for request singlestep. This function should be called, if singlestep should be disabled or is no longer needed. 
 */
void rem_singlestep_req(void);
#endif
