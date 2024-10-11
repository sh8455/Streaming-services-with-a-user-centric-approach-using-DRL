import random
import numpy as np
import math
from queue import Queue

class VideoStreaming:
    def __init__(self, max_chunk_num, num_users):
        # BS의 위치
        self.BS_x = 0
        self.BS_y = 0
        
        self.chunk_length = 5
        self.buffer_capacity = 10
        self.max_chunk_num = max_chunk_num
        self.num_users = num_users
        self.time_step = 0
        self.users = {}
        
        for i in range(self.num_users):
            self.users[i] = {
                'data_availability': random.randint(500, 1000),
                'user_bandwidth': [],
                'user_power': [],
                'user_DR': [],
                'user_distance': [],
                'download_time': [],
                'video_quality': [],
                'transmit_quality': [],
                'step_percentage': [],
                'buffer': [],
                'rebuffering_time': [],
                'buffer_off_time': [],
                'monitor_data_availability': [],
                'play_wait': Queue(self.buffer_capacity),
                'videobuffer': 0,
                'Residual': 0,
                'current_data_availability': 0,
                'current_chunk_num': 0
            }
            
    def reset(self):
        for i in range(self.num_users):
            while not self.users[i]['play_wait'].empty():
                self.users[i]['play_wait'].get()
                
            self.users[i]['data_availability'] = random.randint(500, 1000)
            self.users[i]['user_bandwidth'] = []
            self.users[i]['user_power'] = []
            self.users[i]['user_DR'] = []
            self.users[i]['user_distance'] = []
            self.users[i]['download_time'] = []
            self.users[i]['video_quality'] = []
            self.users[i]['transmit_quality'] = []
            self.users[i]['step_percentage'] = []
            self.users[i]['buffer'] = []
            self.users[i]['rebuffering_time'] = []
            self.users[i]['buffer_off_time'] = []
            self.users[i]['monitor_data_availability'] = []
            self.users[i]['videobuffer'] = 0
            self.users[i]['Residual'] = 0
            self.users[i]['current_data_availability'] = 0
            self.users[i]['current_chunk_num'] = 0
            
        self.time_step = 0
        return self._get_state()
            
    def reset_user_location(self, current_user):
        theta = random.uniform(0, 2 * math.pi)
        r = random.uniform(0, 1000)

        user_x = r * math.cos(theta)
        user_y = r * math.sin(theta)
    
        distance = math.sqrt((self.BS_x - user_x)**2 + (self.BS_y - user_y)**2)
        self.users[current_user]['user_distance'].append(distance)
        return distance
    
    def calculate_user_data_rate(self, bandwidth, power, current_user):
        distance = self.reset_user_location(current_user)
        
        g0 = -50 # dB
        n0 = -174 # dBm
        θ = 2
        
        transmit_g0 = self.transmit_mW(g0)
        transmit_n0 = self.transmit_mW(n0)
        
        channel_gain = transmit_g0 / (distance**θ) # dBm
        transmit_channel_gain = self.transmit_mW(channel_gain)
        
        data_rate = bandwidth * (math.log2((1 + power * transmit_channel_gain) / transmit_n0)) # Mbps
        transmit_data_rate = data_rate * 1000 # kbps
        
        print(f"User{current_user} distance is {distance} m")
        return transmit_data_rate
    
    def transmit_mW(self, value):
        transmit_value = 10 ** (value / 10)
        return transmit_value
    
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
    
    def transmit_number(self, quality):
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
        return transmit_number
    
    def calculate_reward(self):
        done = False
        active_users = 0
        penalty = 0
        
        total_reward = []
        total_bandwidth = []
        total_power = []
        
        sum_reward = 0
        sum_bandwidth = 0
        sum_power = 0
        
        for i in range(self.num_users):
            if self.users[i]['current_chunk_num'] > self.max_chunk_num:
                print(f"User{i} has downloaded all chunks. Skipping reward calculation for this user...")
                continue
            
            active_users += 1
            
            current_quality = self.users[i]['video_quality'][self.time_step]
            prev_quality = self.users[i]['video_quality'][self.time_step - 1]
            
            current_transmit_quality = self.users[i]['transmit_quality'][self.time_step]
            prev_transmit_quality = self.users[i]['transmit_quality'][self.time_step - 1]
            
            current_quality_number = self.transmit_number(current_transmit_quality)
            prev_quality_number = self.transmit_number(prev_transmit_quality)
            
            current_buffer = self.users[i]['buffer'][self.time_step]
            prev_buffer = self.users[i]['buffer'][self.time_step - 1] if self.time_step > 0 else 0
            
            download_time = self.users[i]['download_time'][self.time_step]
            buffer_off_time = self.users[i]['buffer_off_time'][self.time_step]
            rebuffering_time = self.users[i]['rebuffering_time'][self.time_step]
            data_availability = self.users[i]['monitor_data_availability'][self.time_step]
            
            low = 0.4 * data_availability
            
            user_dr = self.users[i]['user_DR'][self.time_step]
            transmit_user_dr = self.transmit_qualities(user_dr)
            
            quality_diff = -abs(prev_quality_number - current_quality_number)
            buffer_diff = prev_buffer - current_buffer
            
            bandwidth = self.users[i]['user_bandwidth'][self.time_step]
            total_bandwidth.append(bandwidth)
            power = self.users[i]['user_power'][self.time_step]
            total_power.append(power)
            
            if transmit_user_dr < current_transmit_quality:
                penalty += -100
                done = True
                
            if data_availability < low:
                penalty += -100
                done = True
            
            qoe = current_transmit_quality + current_buffer + quality_diff + buffer_diff
            latency = download_time + buffer_off_time + rebuffering_time
            reward = qoe + latency + penalty
            
            total_reward.append(reward)
            
        if active_users == 0:
            done = True
            reward = 0
        else:
            for i in range(active_users):
                sum_reward += total_reward[i]
                sum_bandwidth += total_bandwidth[i]
                sum_power += total_power[i]
            
            if sum_bandwidth > 1 or sum_power > 1000:
                reward += -100
                done = True
                
            average_reward = sum_reward / active_users
            
            print(f"sum bandwidth: {sum_bandwidth}, sum power: {sum_power}")
            print(f"reward: {average_reward}")
            
        return average_reward, done
    
    def step(self):
        # 전 스텝에서 청크를 완전히 다운로드 받았을 경우
        done_user = 0
        while done_user < 3:
            for i in range(self.num_users):
                current_user = i
                semi_done_user = 0
                if self.users[i]['current_chunk_num'] >= self.max_chunk_num:
                    print(f"User{i} has downloaded all chunks, Skipping...")
                    done_user += 1
                    continue
                if self.users[i]['Residual'] == 0:
                    bandwidth = random.random()
                    power = random.randint(1, 1000)
                    chunk_quality = random.randint(300, 13000) 
                    transmit_quality = self.transmit_qualities(chunk_quality)
                    
                    user_dr = self.calculate_user_data_rate(bandwidth, power, current_user)
                    transmit_user_dr = self.transmit_qualities(user_dr)
                    self.users[i]['user_DR'].append(user_dr)
                    
                    self.users[i]['user_bandwidth'].append(bandwidth)
                    self.users[i]['user_power'].append(power)
                    self.users[i]['video_quality'].append(chunk_quality)
                    self.users[i]['transmit_quality'].append(transmit_quality)
                    play_time = self.chunk_length
                    
                    print(f"User{i} Bandwidth: {bandwidth}, Power:{power}")
                    print(f"User{i} DR: {user_dr, transmit_user_dr}, Chunk Quality: {chunk_quality, transmit_quality}")
                    print(f"User{i} Chunk[{self.users[i]['current_chunk_num']}] Download Start")
                    
                    chunk_size, download_time, Residual, current_download_percentage  = self.calculate_download(user_dr, chunk_quality, play_time, current_user)
                    
                    print(f"User{i} Download Time: {download_time} sec, Residual: {Residual}")
                    self.users[i]['download_time'].append(download_time)
                    
                    if current_download_percentage >= 100:
                        print(f"User{i} Chunk[{self.users[i]['current_chunk_num']}] Download Complete")
                        self.users[i]['videobuffer'] += self.chunk_length
                        
                        print(f"User{i} Current Buffer is {self.users[i]['videobuffer']}")
                        print(f"User{i} Current Data Availability is {self.users[i]['monitor_data_availability'][self.time_step]}")
                        
                        if self.users[i]['current_chunk_num'] == 0:
                            buffer_off_time = max(max((self.users[i]['videobuffer'] - download_time), 0) + self.chunk_length - self.buffer_capacity, 0)
                        else:
                            buffer_off_time = 0
                        self.users[i]['buffer_off_time'].append(buffer_off_time)
                        
                        rebuffering_time = max((download_time - self.users[i]['videobuffer']), 0)
                        self.users[i]['rebuffering_time'].append(rebuffering_time)
                        
                        self.users[i]['buffer'].append(self.users[i]['videobuffer'])
                        self.users[i]['play_wait'].put(self.users[i]['current_chunk_num'])
                        self.users[i]['current_chunk_num'] += 1
                        self.users[i]['Residual'] = 0
                        semi_done_user += 1
                    else:
                        print(f"User{i} Chunk[{self.users[i]['current_chunk_num']}] is {current_download_percentage} % downloaded")
                        self.users[i]['videobuffer'] += (self.chunk_length * (current_download_percentage/100))
                        
                        print(f"User{i} Current Buffer is {self.users[i]['videobuffer']}")
                        print(f"User{i} Current Data Availability is {self.users[i]['monitor_data_availability'][self.time_step]}")
                        
                        self.users[i]['Residual'] += Residual
                        self.users[i]['buffer'].append(self.users[i]['videobuffer'])
                        
                        if self.users[i]['current_chunk_num'] == 0:
                            buffer_off_time = max(max((self.users[i]['videobuffer'] - download_time), 0) + self.chunk_length - self.buffer_capacity, 0)
                        else:
                            buffer_off_time = 0
                        self.users[i]['buffer_off_time'].append(buffer_off_time)
                        
                        rebuffering_time = max((download_time - self.users[i]['videobuffer']), 0)
                        self.users[i]['rebuffering_time'].append(rebuffering_time)
                        semi_done_user += 1
                # 전 스텝에서 청크를 완전히 다운받지 않았을 경우
                else:
                    bandwidth = random.random()
                    power = random.randint(1, 1000)
                    chunk_quality = random.randint(300, 13000) 
                    transmit_quality = self.transmit_qualities(chunk_quality)
                    
                    user_dr = self.calculate_user_data_rate(bandwidth, power, current_user)
                    transmit_user_dr = self.transmit_qualities(user_dr)
                    self.users[i]['user_DR'].append(user_dr)
                    
                    self.users[i]['user_bandwidth'].append(bandwidth)
                    self.users[i]['user_power'].append(power)
                    self.users[i]['video_quality'].append(chunk_quality)
                    self.users[i]['transmit_quality'].append(transmit_quality)
                    
                    print(f"User{i} Bandwidth: {bandwidth}, Power:{power}")
                    print(f"User{i} DR: {user_dr, transmit_user_dr}, Chunk Quality: {chunk_quality, transmit_quality}")
                    print(f"User{i} Chunk[{self.users[i]['current_chunk_num']}] Redownload Start")
                    
                    play_time = self.chunk_length - (self.chunk_length * (self.users[i]['step_percentage'][self.time_step - 1] / 100))
                    
                    chunk_size, download_time, Residual, current_download_percentage = self.calculate_download(user_dr, chunk_quality, play_time, current_user)
                    
                    print(f"User{i} Download Time: {download_time} sec, Residual: {Residual}")
                    
                    if current_download_percentage >= 100:
                        print(f"User{i} Chunk[{self.users[i]['current_chunk_num']}] Download Complete")
                        self.users[i]['videobuffer'] += play_time
                        self.users[i]['Residual'] = 0
                        self.users[i]['buffer'].append(self.users[i]['videobuffer'])
                        self.users[i]['play_wait'].put(self.users[i]['current_chunk_num'])
                        
                        print(f"User{i} Current Buffer is {self.users[i]['videobuffer']}")
                        print(f"User{i} Current Data Availability is {self.users[i]['monitor_data_availability'][self.time_step]}")
                        
                        if self.users[i]['current_chunk_num'] == 0:
                            buffer_off_time = max(max((self.users[i]['videobuffer'] - download_time), 0) + self.chunk_length - self.buffer_capacity, 0)
                        else:
                            buffer_off_time = 0
                        self.users[i]['buffer_off_time'].append(buffer_off_time)
                        
                        rebuffering_time = max((download_time - self.users[i]['videobuffer']), 0)
                        self.users[i]['rebuffering_time'].append(rebuffering_time)
                        
                        self.users[i]['current_chunk_num'] += 1
                        semi_done_user += 1
                    else:
                        print(f"User{i} Chunk[{self.users[i]['current_chunk_num']}] is {current_download_percentage} % downloadad")
                        self.users[i]['videobuffer'] += play_time
                        self.users[i]['Residual'] += Residual
                        self.users[i]['buffer'].append(self.users[i]['videobuffer'])
                        
                        print(f"User{i} Current Buffer is {self.users[i]['videobuffer']}")
                        print(f"User{i} Current Data Availability is {self.users[i]['monitor_data_availability'][self.time_step]}")
                        
                        if self.users[i]['current_chunk_num'] == 0:
                            buffer_off_time = max(max((self.users[i]['videobuffer'] - download_time), 0) + self.chunk_length - self.buffer_capacity, 0)
                        else:
                            buffer_off_time = 0
                        self.users[i]['buffer_off_time'].append(buffer_off_time)
                        
                        rebuffering_time = max((download_time - self.users[i]['videobuffer']), 0)
                        self.users[i]['rebuffering_time'].append(rebuffering_time)
                        semi_done_user += 1
                    
                if self.users[i]['videobuffer']:
                    if self.users[i]['play_wait'].qsize() >= self.buffer_capacity:
                        current_chunk = self.users[i]['play_wait'].get()
                        self.users[i]['videobuffer'] -= 5
                        print(f"User{i} Chunk[{current_chunk}] is Playing...")
                        
                # reward, done = self.calculate_reward()
                
                if semi_done_user == 3:
                    self.time_step += 1
                    
                if done == False:
                    if done_user == 3:
                        done = True       
                # return self._get_state(), reward, done, {}
    
    def calculate_download(self, user_dr, chunk_quality, play_time, current_user):
        chunk_size = chunk_quality * play_time
        download_time = chunk_size / user_dr
        
        if download_time <= 1:
            download_time = 1
        else:
            download_time = chunk_size / user_dr
        self.users[current_user]['download_time'].append(download_time)
        
        download_in_sec = chunk_size / download_time
        
        if download_in_sec * 5 > chunk_size:
            download_in_current_step = chunk_size
        else:
            download_in_current_step = download_in_sec * 5
        
        if download_in_current_step >= chunk_size:
            Residual = 0
        else:
            Residual = chunk_size - download_in_current_step
            
        transmit_mb = download_in_current_step / 8000
        
        if self.time_step == 0:
            current_data_availability = self.users[current_user]['data_availability'] - transmit_mb
        else:
            current_data_availability = self.users[current_user]['monitor_data_availability'][self.time_step - 1] - transmit_mb
        self.users[current_user]['monitor_data_availability'].append(current_data_availability) 
        
        # current_data_availability = self.data_availability - self.current_data_availability
        # self.monitor_data_availability.append(current_data_availability)
        
        current_download_percentage = (download_in_current_step / chunk_size) * 100
        self.users[current_user]['step_percentage'].append(current_download_percentage)
        return chunk_size, download_time, Residual, current_download_percentage
    
    def _get_state(self):
        obs = []
        
        for i in range(self.num_users):
            if self.users[i]['current_chunk_num'] < self.max_chunk_num:
                prev_quality = self.users[i]['video_quality'][self.time_step - 1] if self.time_step > 0 else self.users[i]['video_quality'][self.time_step]
                prev_buffer = self.users[i]['buffer'][self.time_step - 1] if self.time_step > 0 else self.users[i]['buffer'][self.time_step]
                data_availability = self.users[i]['monitor_data_availability'][self.time_step]
                user_DR = self.users[i]['user_DR'][self.time_step]
                user_distance = self.users[i]['user_distance'][self.time_step]
                
                user_state = [prev_quality, prev_buffer, data_availability, user_DR, user_distance]
            else:
                prev_quality = 0
                prev_buffer = 0
                data_availability = 0
                user_DR = 0
                user_distance = 0
                
                user_state = [prev_quality, prev_buffer, data_availability, user_DR, user_distance]
                
            obs.extend(user_state)
        return np.array(obs)
            
    
videostreaming = VideoStreaming(20, 3)
videostreaming.step()