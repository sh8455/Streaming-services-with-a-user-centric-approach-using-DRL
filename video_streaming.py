import random
import numpy as np
import math
from queue import Queue

class VideoStreaming:
    def __init__(self, max_chunk_num, num_users, data_availability):
        # BS의 위치
        self.BS_X = 0
        self.BS_Y = 0
        
        self.chunk_length = 5 # 청크 재생 시간
        self.max_chunk_num = max_chunk_num # 청크의 최대 갯수
        self.buffer_capacity = self.max_chunk_num * self.chunk_length # 버퍼의 최대 용량 (재생 시간 기준)
        self.num_users = num_users # 사용자의 수
        
        self.data_availability = data_availability
        
        self.time_step = 0 # 타임 스텝 카운트를 위한 변수
        self.users = {} # 사용자의 정보가 담긴 딕셔너리
        
        for i in range(self.num_users):
            self.users[i] = {
                'data_availability': self.data_availability, # 데이터 가용량
                'user_bandwidth': [], # 타임스텝별 할당된 대역폭을 담을 리스트
                'user_power': [], # 타임스텝별 할당된 전력을 담을 리스트
                'user_DR': [], # 타임스텝별 사용자의 data rate를 담을 리스트
                'user_distance': [], # 타임스텝별 사용자와 BS 사이의 거리를 담을 리스트
                'video_quality': [], # 타임스텝별 할당된 청크의 화질을 담을 리스트
                'buffer': [], # 타임스텝별 사용자의 버퍼량을 담을 리스트 (재생 시간 기준)
                'rebuffering_time': [], # 타임스텝별 사용자의 리버퍼링 시간을 담을 리스트
                'buffer_off_time': [], # 타임스텝별 사용자의 버퍼 오프 시간을 담을 리스트
                'monitor_data_availability': [], # 타임스텝별 사용자의 잔여 데이터 가용량을 담을 리스트
                'step_per_qoe': [], # 타임스텝별 사용자의 qoe를 담을 리스트
                'step_per_download': [], # 타임스텝별 사용자의 다운로드된 청크 개수를 담을 리스트 
                'step_per_download_floor': [],
                'play_wait': Queue(self.buffer_capacity), # 사용자의 청크 재생을 위한 버퍼 (청크 번호 기준)
                'videobuffer': 0, # 타임스텝별 사용자의 버퍼량을 계산하기 위한 변수
                'current_chunk_num': 0, # 현재 타임스텝의 다운로드 받아야 할 청크 넘버를 알기 위한 변수
                'remaining_chunk': self.max_chunk_num, # 남은 청크 갯수를 알기 위한 변수
            }
    
    def reset(self):
        for i in range(self.num_users):
            while not self.users[i]['play_wait'].empty():
                self.users[i]['play_wait'].get()
                
            self.users[i]['data_availability'] = self.data_availability
            self.users[i]['user_bandwidth'] = []
            self.users[i]['user_power'] = []
            self.users[i]['user_DR'] = []
            self.users[i]['user_distance'] = []
            self.users[i]['video_quality'] = []
            self.users[i]['buffer'] = []
            self.users[i]['rebuffering_time'] = []
            self.users[i]['buffer_off_time'] = []
            self.users[i]['monitor_data_availability'] = []
            self.users[i]['step_per_qoe'] = []
            self.users[i]['step_per_download'] = []
            self.users[i]['step_per_download_floor'] = []
            self.users[i]['videobuffer'] = 0
            self.users[i]['current_chunk_num'] = 0
            self.users[i]['remaining_chunk'] = self.max_chunk_num
            
            self.users[i]['monitor_data_availability'].append(self.users[i]['data_availability'])
            
        self.time_step = 0
        
        return self._get_state()
    
    # 유저의 위치 설정 (BS와의 거리 계산)        
    def reset_user_location(self, current_user):
        theta = random.uniform(0, 2 * math.pi)
        r = random.uniform(0, 1000) # 1km의 거리 가정
        
        user_x = r * math.cos(theta)
        user_y = r * math.sin(theta)
        
        distance = math.sqrt((self.BS_X - user_x)**2 + (self.BS_Y - user_y)**2)
        self.users[current_user]['user_distance'].append(distance)
        
        return distance
    
    # Data Rate 계산
    def calculate_user_data_rate(self, bandwidth, power, current_user):
        distance = self.reset_user_location(current_user)
        
        g0 = -50 # db
        n0 = -174 # dBm
        θ = 2
        
        transmit_g0 = self.transmit_mW(g0)
        transmit_n0 = self.transmit_mW(n0)
        
        channel_gain = transmit_g0 / (distance**θ) # dBm
        transmit_channel_gain = self.transmit_mW(channel_gain)
        
        data_rate = bandwidth * (math.log2((1 + power * transmit_channel_gain / transmit_n0))) # Mbps
        transmit_data_rate = data_rate * 1000 # Kbps
        
        print(f"User{current_user} distance is {distance}m")
        
        return transmit_data_rate
        
    # mW 단위 변경
    def transmit_mW(self, value):
        transmit_value = 10 ** (value / 10)
        
        return transmit_value
    
    # Kbps -> 화질(p)로 치환
    def transmit_qualities(self, quality):
        transmit_quality = None
        if 300 <= quality <= 400 or quality < 300:
            transmit_quality = 240
        elif 400 < quality <= 1000:
            transmit_quality = 360
        elif 1000 < quality <= 2000:
            transmit_quality = 480
        elif 2000 < quality <= 4000:
            transmit_quality = 720
        elif 4000 < quality <= 6000:
            transmit_quality = 1080
        elif 6000 < quality <= 13000 or quality > 13000:
            transmit_quality = 1440
        
        return transmit_quality
    
    # 액션으로 받은 화질 넘버 -> 실제 화질(p)로 치환            
    def transmit_action_quality(self, action_quality):
        real_quality = None
        if action_quality == 0:
            real_quality = 240
        elif action_quality == 1:
            real_quality = 360
        elif action_quality == 2:
            real_quality = 480
        elif action_quality == 3:
            real_quality = 720
        elif action_quality == 4:
            real_quality = 1080
        else:
            real_quality = 1440
            
        return real_quality
    
    # 액션으로 받은 화질 -> kbps로 치환
    def transmit_action_kbps(self, quality):
        transmit_kbps = None
        if quality == 240:
            # transmit_kbps = random.randint(300, 700)
            transmit_kbps = 700
        elif quality == 360:
            # transmit_kbps = random.randint(701, 1000)
            transmit_kbps = 1000
        elif quality == 480:
            # transmit_kbps = random.randint(1001, 2000)
            transmit_kbps = 2000
        elif quality == 720:
            # transmit_kbps = random.randint(2001, 4000)
            transmit_kbps = 4000
        elif quality == 1080:
            # transmit_kbps = random.randint(4001, 6000)
            transmit_kbps = 6000
        else:
            # transmit_kbps = random.randint(6001, 13000)
            transmit_kbps = 13000
            
        return transmit_kbps
    
    # 화질 -> 숫자로 치환
    def transmit_quality_number(self, quality):
        transmit_number = None
        if quality == 240:
            transmit_number = 1
        elif quality == 360:
            transmit_number = 2
        elif quality == 480:
            transmit_number = 3
        elif quality == 720:
            transmit_number = 4
        elif quality == 1080:
            transmit_number = 5
        elif quality == 1440:
            transmit_number = 6
        else:
            transmit_number = 0
            
        return transmit_number
    
    def calculate_download_chunk(self, user_dr, chunk_quality, current_user):
        chunk_size = chunk_quality * self.chunk_length # 할당된 화질을 가지고 계산하는 청크 하나당 사이즈
        
        download_in_step = user_dr * self.chunk_length # 유저가 한 스텝당 다운가능한 양
        Number_of_pdchunk = round(download_in_step / chunk_size, 1) # 유저가 한 스텝당 다운가능한 청크 갯수 
        
        # 다운 받은 청크의 개수가 남은 청크 개수보다 크거나 같으면
        if Number_of_pdchunk >= self.users[current_user]['remaining_chunk']:
            Number_of_pdchunk = round(self.users[current_user]['remaining_chunk'], 1)
            self.users[current_user]['remaining_chunk'] = 0
        else:
            remaining_chunk = round(self.users[current_user]['remaining_chunk'] - Number_of_pdchunk, 1)
            self.users[current_user]['remaining_chunk'] = remaining_chunk
            
            
        self.users[current_user]['step_per_download'].append(Number_of_pdchunk) # 스텝별 현재 다운로드량
        
        print(f"다운 가능한 청크 양: {Number_of_pdchunk}")
            
        return Number_of_pdchunk, chunk_size
    
    def calculate_qoe(self):
        done = False
        active_users = 0
        penalty = 0
        
        for i in range(self.num_users):
            if self.users[i]['current_chunk_num'] >= self.max_chunk_num + 1:
                print(f"User{i} has downloaded all chunks. Skipping reward calculation...")
                continue

            print(f"current calculation user is User{i}")
            print(f"current time step is {self.time_step}")
            
            active_users += 1
            
            current_quality = self.users[i]['video_quality'][self.time_step]
            prev_quality = self.users[i]['video_quality'][self.time_step - 1] if self.time_step > 0 else 0
            
            current_quality_number = self.transmit_quality_number(current_quality)
            prev_quality_number = self.transmit_quality_number(prev_quality)
            
            transmit_quality_kbps = self.transmit_action_kbps(current_quality)
            
            current_buffer = self.users[i]['buffer'][self.time_step]
            prev_buffer = self.users[i]['buffer'][self.time_step - 1] if self.time_step > 0 else 0
            
            buffer_off_time = self.users[i]['buffer_off_time'][self.time_step]
            rebuffering_time = self.users[i]['rebuffering_time'][self.time_step]
            data_availability = self.users[i]['monitor_data_availability'][-1]
            
            low = 0.4 * data_availability
            
            user_dr = self.users[i]['user_DR'][self.time_step]
            transmit_user_dr = self.transmit_qualities(user_dr)
            
            quality_diff = -abs(prev_quality_number - current_quality_number)
            buffer_diff = prev_buffer - current_buffer
            
            if data_availability > low and transmit_user_dr < current_quality:
                penalty += -1000
                done = True
                
            if data_availability < low:
                penalty += -1000
                done = True
            
            quality_loss = user_dr - transmit_quality_kbps
            
            if quality_loss < 0:
                quality_loss = quality_loss
            elif quality_loss > 0:
                quality_loss = -quality_loss
                
            qoe = current_quality + user_dr + quality_diff + buffer_diff + quality_loss
            latency = -(buffer_off_time + rebuffering_time)
            
            QoE = qoe + latency +penalty
            
            self.users[i]['step_per_qoe'].append(QoE)
            
            if self.users[i]['current_chunk_num'] == self.max_chunk_num:
                self.users[i]['current_chunk_num'] += 1
            
            print(f"User{i} QoE: {QoE}")
    
        return done
    
    # 한 에피소드당 모든 유저의 reward 계산
    def calculate_reward(self):
        total_qoe = 0
        total_time_step = 0
        
        for i in range(self.num_users):
            total_qoe += sum(self.users[i]['step_per_qoe'])
            total_time_step += len(self.users[i]['step_per_qoe'])
            print(f"User{i} total qoe: {sum(self.users[i]['step_per_qoe'])}")
            print(f"User{i} total time step: {len(self.users[i]['step_per_qoe'])}")
            
        reward = total_qoe / total_time_step
        
        print(f"episode per reward: {reward}")
        
        return reward
    
    def step(self, action):
        done_user = 0
        action_dim_per_user = 3
        sum_bandwidth = 0
        sum_power = 0
        print(f"action: {action}")
        reshape_action = action.reshape((self.num_users, action_dim_per_user))
        
        # 대역폭과 전력의 총합 계산
        for i in range(self.num_users):
            action_bandwidth, action_power, action_chunk_quality = reshape_action[i]
            sum_bandwidth += 0.1 * action_bandwidth + 0.05
            sum_power += 0.1 * action_power + 0.05
            
        print(f"sum_bandwidth: {sum_bandwidth}, sum_power: {sum_power}")
        
        for i in range(self.num_users):
            # 청크를 모두 다운로드 받은 사용자는 다운로딩 스킵
            if self.users[i]['current_chunk_num'] >= self.max_chunk_num:
                print(f"User{i} has downloaded all chunks, Skipping...")
                done_user += 1
                print(f"done user: {done_user}")
                continue
            
            # 큐에 5개 이상의 청크가 차 있으면 재생 시작 (한 청크씩 재생)
            if self.users[i]['videobuffer']:
                if self.users[i]['play_wait'].qsize() >= 5:
                    current_chunk = self.users[i]['play_wait'].get()
                    self.users[i]['videobuffer'] -= self.chunk_length
                    print(f"User{i} Chunk[{current_chunk}] is Playing...")
                    
            # 대역폭, 전력, 화질 할당
            user_action = reshape_action[i]
            action_bandwidth, action_power, action_chunk_quality = user_action
            bandwidth = (0.1 * action_bandwidth + 0.05) / sum_bandwidth
            power = (0.1 * action_power + 0.05) / sum_power
            chunk_quality = self.transmit_action_quality(action_chunk_quality)
            quality_kbps = self.transmit_action_kbps(chunk_quality)
            
            self.users[i]['video_quality'].append(chunk_quality)
            
            # 사용자의 Data Rate 계산
            user_dr = math.floor(self.calculate_user_data_rate(bandwidth, power, i))
            self.users[i]['user_DR'].append(user_dr)
            
            print(f"User{i} bandwidth: {bandwidth}, power: {power}")
            print(f"User{i} DR: {user_dr}, Video Quality: {quality_kbps}Kbps, {chunk_quality}p")
            
            # 청크 다운로드 시작
            print(f"User{i} Download Start, Remaining Chunk: {self.users[i]['remaining_chunk']}")
            Number_of_pdchunk, chunk_size = self.calculate_download_chunk(user_dr, quality_kbps, i)
            
            # 현 스텝에서 큐에 넣을 청크 개수 계산
            if self.time_step == 0:
                put_queue = math.floor(Number_of_pdchunk)
                self.users[i]['step_per_download_floor'].append(put_queue)
            else:
                put_queue = math.floor(round(sum(self.users[i]['step_per_download'],1)) - sum(self.users[i]['step_per_download_floor']))
                print(f"sum 현재 다운로드: {sum(self.users[i]['step_per_download'])}, floor 다운로드: {sum(self.users[i]['step_per_download_floor'])}")
                print(f"floor 다운로드: {self.users[i]['step_per_download_floor']}")
                self.users[i]['step_per_download_floor'].append(put_queue)
            
            print(f"현재 다운로드: {self.users[i]['step_per_download']}")
            
            print(f"User{i} 현스텝 다운받은 청크개수: {Number_of_pdchunk}, 완전히 다운받은 청크개수: {put_queue}")
            print(f"User{i}의 남은 청크개수: {self.users[i]['remaining_chunk']}")
            print(f"User{i}의 현재 청크 번호: {self.users[i]['current_chunk_num']}")
            
            transmit_mb = (Number_of_pdchunk * chunk_size) / 8000 # 다운로드 후 모바일 소진량
            self.users[i]['monitor_data_availability'].append(self.users[i]['monitor_data_availability'][-1] - transmit_mb)
            print(f"User{i} Data Usage: {transmit_mb}MB, remaining data availability: {self.users[i]['monitor_data_availability'][-1]}")       
            
            # 비디오 버퍼에 다운받은 만큼 재생 시간 추가
            self.users[i]['videobuffer'] += self.chunk_length * Number_of_pdchunk
            self.users[i]['buffer'].append(self.users[i]['videobuffer'])
            print(f"User{i} current buffer: {self.users[i]['videobuffer']}sec")
            
            # buffer off time과 rebuffering time 계산
            if self.users[i]['videobuffer'] == 0 or self.time_step == 0:
                buffer_off_time = max(max((self.users[i]['videobuffer'] - self.chunk_length), 0) + self.chunk_length - self.buffer_capacity, 0)
            else:
                buffer_off_time = 0
            self.users[i]['buffer_off_time'].append(buffer_off_time)
            
            if self.users[i]['videobuffer'] == 0:
                rebuffering_time = max((self.chunk_length - self.users[i]['videobuffer']), 0)
            else:
                rebuffering_time = 0
            self.users[i]['rebuffering_time'].append(rebuffering_time)
            
            print(f"buffer off time: {buffer_off_time}, rebuffering time: {rebuffering_time}")
            
            # 큐에 다운받은 청크 개수만큼 청크 추가
            for j in range(put_queue):
                self.users[i]['current_chunk_num'] += 1
                self.users[i]['play_wait'].put(self.users[i]['current_chunk_num'])
                print(f"User{i} Input Chunk: {self.users[i]['current_chunk_num']}")
                    
        print(f"Current Time Step is {self.time_step}")
        
        done = self.calculate_qoe()
        
        # 모든 사용자의 다운로드가 한번씩 끝났으면 타임 스텝 추가
        self.time_step += 1
        
        if done == True:
            return self._get_state(), -100, done, {}
        
        if done_user == 3:
            reward = self.calculate_reward()
            return self._get_state(), reward, True, {}
        return self._get_state(), 0, False, {}
        
    def _get_state(self):
        obs = []
        
        for i in range(self.num_users):
            if self.users[i]['current_chunk_num'] < self.max_chunk_num:
                if self.time_step == 0:
                    prev_quality = 0
                    prev_buffer = 0
                    data_availability = self.users[i]['data_availability']
                    user_distance = 0
                else:
                    prev_quality = self.users[i]['video_quality'][self.time_step - 1] if self.time_step > 0 else 0
                    prev_buffer = self.users[i]['buffer'][self.time_step - 1] if self.time_step > 0 else 0
                    data_availability = self.users[i]['monitor_data_availability'][-1]
                    user_distance = self.users[i]['user_distance'][self.time_step - 1]
                
                user_state = [prev_quality, prev_buffer, data_availability, user_distance]
            else:
                prev_quality = 0
                prev_buffer = 0
                data_availability = 0
                user_distance = 0
                
                user_state = [prev_quality, prev_buffer, data_availability, user_distance]
                
            obs.extend(user_state)
        print(obs)
        return np.array(obs) 
                

            
        
        
