"""
LAM-A2E API 测试脚本

测试所有API接口的功能和性能

使用方法:
    python test_api.py --host localhost --port 8000
    python test_api.py --test-audio assets/sample_audio/BarackObama_english.wav
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
from typing import Optional

import requests
import numpy as np


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")


def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")


def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.RESET}")


def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.RESET}")


def print_header(msg):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{msg}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")


class APITester:
    def __init__(self, base_url: str, test_audio: str):
        self.base_url = base_url
        self.test_audio = test_audio
        self.session_id = None
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'total': 0
        }
    
    def run_test(self, test_name: str, test_func):
        """运行单个测试"""
        self.test_results['total'] += 1
        print(f"\n{Colors.BOLD}测试 {self.test_results['total']}: {test_name}{Colors.RESET}")
        print("-" * 60)
        
        try:
            start_time = time.time()
            test_func()
            elapsed = time.time() - start_time
            
            self.test_results['passed'] += 1
            print_success(f"测试通过 (耗时: {elapsed:.2f}秒)")
            return True
        except AssertionError as e:
            self.test_results['failed'] += 1
            print_error(f"测试失败: {str(e)}")
            return False
        except Exception as e:
            self.test_results['failed'] += 1
            print_error(f"测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_root_endpoint(self):
        """测试根路径"""
        print_info("GET /")
        response = requests.get(f"{self.base_url}/")
        
        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        data = response.json()
        
        assert 'service' in data, "缺少 service 字段"
        assert 'version' in data, "缺少 version 字段"
        assert 'endpoints' in data, "缺少 endpoints 字段"
        
        print_info(f"服务: {data['service']}")
        print_info(f"版本: {data['version']}")
        print_info(f"可用端点: {len(data['endpoints'])} 个")
    
    def test_health_check(self):
        """测试健康检查"""
        print_info("GET /api/health")
        response = requests.get(f"{self.base_url}/api/health")
        
        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        data = response.json()
        
        assert 'status' in data, "缺少 status 字段"
        assert 'model_loaded' in data, "缺少 model_loaded 字段"
        assert 'gpu_available' in data, "缺少 gpu_available 字段"
        assert 'sessions' in data, "缺少 sessions 字段"
        
        print_info(f"状态: {data['status']}")
        print_info(f"模型已加载: {data['model_loaded']}")
        print_info(f"GPU可用: {data['gpu_available']}")
        print_info(f"活跃会话: {data['sessions']}")
        
        assert data['status'] == 'healthy', "服务状态不健康"
        assert data['model_loaded'] == True, "模型未加载"
    
    def test_standard_inference_basic(self):
        """测试标准推理（基础参数）"""
        print_info("POST /api/infer (基础参数)")
        
        if not os.path.exists(self.test_audio):
            raise FileNotFoundError(f"测试音频文件不存在: {self.test_audio}")
        
        files = {'audio_file': open(self.test_audio, 'rb')}
        data = {'id_idx': 0}
        
        response = requests.post(
            f"{self.base_url}/api/infer",
            files=files,
            data=data
        )
        
        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        result = response.json()
        
        # 验证响应结构
        assert 'names' in result, "缺少 names 字段"
        assert 'metadata' in result, "缺少 metadata 字段"
        assert 'frames' in result, "缺少 frames 字段"
        
        # 验证 metadata
        metadata = result['metadata']
        assert 'fps' in metadata, "缺少 fps 字段"
        assert 'frame_count' in metadata, "缺少 frame_count 字段"
        assert 'blendshape_count' in metadata, "缺少 blendshape_count 字段"
        assert 'inference_time' in metadata, "缺少 inference_time 字段"
        
        # 验证数据
        assert len(result['names']) == 52, f"Blendshape数量错误: {len(result['names'])}"
        assert metadata['fps'] == 30.0, f"FPS错误: {metadata['fps']}"
        assert metadata['blendshape_count'] == 52, f"Blendshape计数错误"
        assert len(result['frames']) == metadata['frame_count'], "帧数不匹配"
        
        # 验证第一帧
        first_frame = result['frames'][0]
        assert 'weights' in first_frame, "帧缺少 weights 字段"
        assert 'time' in first_frame, "帧缺少 time 字段"
        assert len(first_frame['weights']) == 52, f"权重数量错误: {len(first_frame['weights'])}"
        
        # 验证权重范围
        for weight in first_frame['weights']:
            assert 0.0 <= weight <= 1.0, f"权重超出范围: {weight}"
        
        print_info(f"生成帧数: {metadata['frame_count']}")
        print_info(f"推理耗时: {metadata['inference_time']:.3f}秒")
        print_info(f"平均每帧: {metadata['inference_time']/metadata['frame_count']*1000:.2f}ms")
    
    def test_standard_inference_full_params(self):
        """测试标准推理（完整参数）"""
        print_info("POST /api/infer (完整参数)")
        
        files = {'audio_file': open(self.test_audio, 'rb')}
        data = {
            'id_idx': 0,
            'ex_vol': False,  # 设为True会很慢
            'movement_smooth': True,
            'brow_movement': True
        }
        
        response = requests.post(
            f"{self.base_url}/api/infer",
            files=files,
            data=data
        )
        
        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        result = response.json()
        
        assert len(result['frames']) > 0, "未生成任何帧"
        print_info(f"生成帧数: {result['metadata']['frame_count']}")
        print_info(f"推理耗时: {result['metadata']['inference_time']:.3f}秒")
    
    def test_standard_inference_different_ids(self):
        """测试不同的身份ID"""
        print_info("POST /api/infer (测试不同ID)")
        
        test_ids = [0, 5, 11]  # streaming模型支持0-11
        
        for id_idx in test_ids:
            files = {'audio_file': open(self.test_audio, 'rb')}
            data = {'id_idx': id_idx}
            
            response = requests.post(
                f"{self.base_url}/api/infer",
                files=files,
                data=data
            )
            
            assert response.status_code == 200, f"ID {id_idx} 推理失败"
            result = response.json()
            assert len(result['frames']) > 0, f"ID {id_idx} 未生成帧"
            
            print_info(f"ID {id_idx}: 生成 {result['metadata']['frame_count']} 帧")
    
    def test_streaming_init(self):
        """测试流式推理初始化"""
        print_info("POST /api/infer_stream_init")
        
        payload = {'id_idx': 0}
        response = requests.post(
            f"{self.base_url}/api/infer_stream_init",
            json=payload
        )
        
        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        data = response.json()
        
        assert 'session_id' in data, "缺少 session_id 字段"
        assert 'message' in data, "缺少 message 字段"
        assert 'id_idx' in data, "缺少 id_idx 字段"
        
        self.session_id = data['session_id']
        print_info(f"会话ID: {self.session_id}")
        print_info(f"消息: {data['message']}")
    
    def test_streaming_chunk(self):
        """测试流式推理处理chunk"""
        print_info("POST /api/infer_stream_chunk")
        
        # 先初始化会话
        if self.session_id is None:
            payload = {'id_idx': 0}
            response = requests.post(
                f"{self.base_url}/api/infer_stream_init",
                json=payload
            )
            self.session_id = response.json()['session_id']
            print_info(f"创建新会话: {self.session_id}")
        
        # 发送音频chunk
        files = {'audio_chunk': open(self.test_audio, 'rb')}
        data = {'session_id': self.session_id}
        
        response = requests.post(
            f"{self.base_url}/api/infer_stream_chunk",
            files=files,
            data=data
        )
        
        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        result = response.json()
        
        # 验证响应
        assert 'metadata' in result, "缺少 metadata 字段"
        metadata = result['metadata']
        
        assert 'session_id' in metadata, "缺少 session_id 字段"
        assert 'chunk_index' in metadata, "缺少 chunk_index 字段"
        assert 'inference_time' in metadata, "缺少 inference_time 字段"
        
        assert metadata['session_id'] == self.session_id, "会话ID不匹配"
        
        print_info(f"Chunk索引: {metadata['chunk_index']}")
        print_info(f"生成帧数: {metadata['frame_count']}")
        print_info(f"推理耗时: {metadata['inference_time']:.3f}秒")
    
    def test_streaming_multiple_chunks(self):
        """测试流式推理处理多个chunk"""
        print_info("POST /api/infer_stream_chunk (多个chunk)")
        
        # 初始化会话
        payload = {'id_idx': 0}
        response = requests.post(
            f"{self.base_url}/api/infer_stream_init",
            json=payload
        )
        session_id = response.json()['session_id']
        print_info(f"会话ID: {session_id}")
        
        # 发送3个chunk
        num_chunks = 3
        total_frames = 0
        total_time = 0
        
        for i in range(num_chunks):
            files = {'audio_chunk': open(self.test_audio, 'rb')}
            data = {'session_id': session_id}
            
            start = time.time()
            response = requests.post(
                f"{self.base_url}/api/infer_stream_chunk",
                files=files,
                data=data
            )
            elapsed = time.time() - start
            
            assert response.status_code == 200, f"Chunk {i+1} 失败"
            result = response.json()
            
            chunk_idx = result['metadata']['chunk_index']
            frame_count = result['metadata']['frame_count']
            inference_time = result['metadata']['inference_time']
            
            assert chunk_idx == i + 1, f"Chunk索引错误: 期望{i+1}, 实际{chunk_idx}"
            
            total_frames += frame_count
            total_time += inference_time
            
            print_info(f"Chunk {chunk_idx}: {frame_count}帧, "
                      f"推理{inference_time:.3f}秒, "
                      f"总耗时{elapsed:.3f}秒")
        
        print_info(f"总计: {num_chunks}个chunk, {total_frames}帧, "
                  f"平均推理时间{total_time/num_chunks:.3f}秒")
        
        # 清理会话
        self.session_id = session_id
    
    def test_streaming_close(self):
        """测试关闭流式会话"""
        print_info("DELETE /api/infer_stream_close/{session_id}")
        
        # 如果没有会话，先创建一个
        if self.session_id is None:
            payload = {'id_idx': 0}
            response = requests.post(
                f"{self.base_url}/api/infer_stream_init",
                json=payload
            )
            self.session_id = response.json()['session_id']
            print_info(f"创建测试会话: {self.session_id}")
        
        # 关闭会话
        response = requests.delete(
            f"{self.base_url}/api/infer_stream_close/{self.session_id}"
        )
        
        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        data = response.json()
        
        assert 'message' in data, "缺少 message 字段"
        assert 'session_id' in data, "缺少 session_id 字段"
        assert data['session_id'] == self.session_id, "会话ID不匹配"
        
        print_info(f"消息: {data['message']}")
        
        # 验证会话已关闭（再次关闭应该返回404）
        response = requests.delete(
            f"{self.base_url}/api/infer_stream_close/{self.session_id}"
        )
        assert response.status_code == 404, "会话未正确关闭"
        
        self.session_id = None
    
    def test_error_handling_invalid_audio(self):
        """测试错误处理：无效音频"""
        print_info("测试错误处理：无效音频文件")
        
        # 创建一个无效的文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is not an audio file")
            temp_file = f.name
        
        try:
            files = {'audio_file': open(temp_file, 'rb')}
            data = {'id_idx': 0}
            
            response = requests.post(
                f"{self.base_url}/api/infer",
                files=files,
                data=data
            )
            
            assert response.status_code in [400, 500], \
                f"应该返回错误状态码，实际: {response.status_code}"
            
            print_info(f"正确返回错误状态码: {response.status_code}")
        finally:
            os.remove(temp_file)
    
    def test_error_handling_invalid_session(self):
        """测试错误处理：无效会话ID"""
        print_info("测试错误处理：无效会话ID")
        
        fake_session_id = "00000000-0000-0000-0000-000000000000"
        
        files = {'audio_chunk': open(self.test_audio, 'rb')}
        data = {'session_id': fake_session_id}
        
        response = requests.post(
            f"{self.base_url}/api/infer_stream_chunk",
            files=files,
            data=data
        )
        
        assert response.status_code == 404, \
            f"应该返回404，实际: {response.status_code}"
        
        print_info("正确返回404错误")
    
    def test_performance_benchmark(self):
        """性能基准测试"""
        print_info("性能基准测试")
        
        num_runs = 3
        times = []
        
        for i in range(num_runs):
            files = {'audio_file': open(self.test_audio, 'rb')}
            data = {'id_idx': 0}
            
            start = time.time()
            response = requests.post(
                f"{self.base_url}/api/infer",
                files=files,
                data=data
            )
            elapsed = time.time() - start
            
            assert response.status_code == 200, f"运行 {i+1} 失败"
            
            result = response.json()
            inference_time = result['metadata']['inference_time']
            frame_count = result['metadata']['frame_count']
            
            times.append(inference_time)
            
            print_info(f"运行 {i+1}: {inference_time:.3f}秒 "
                      f"({frame_count}帧, "
                      f"{inference_time/frame_count*1000:.2f}ms/帧)")
        
        avg_time = np.mean(times)
        std_time = np.std(times)
        
        print_info(f"平均推理时间: {avg_time:.3f} ± {std_time:.3f}秒")
        print_info(f"最快: {min(times):.3f}秒")
        print_info(f"最慢: {max(times):.3f}秒")
    
    def test_output_validation(self):
        """验证输出数据的正确性"""
        print_info("验证输出数据")
        
        files = {'audio_file': open(self.test_audio, 'rb')}
        data = {'id_idx': 0, 'movement_smooth': True, 'brow_movement': True}
        
        response = requests.post(
            f"{self.base_url}/api/infer",
            files=files,
            data=data
        )
        
        result = response.json()
        
        # 验证ARKit blendshape名称
        expected_names = [
            "browDownLeft", "browDownRight", "browInnerUp", 
            "browOuterUpLeft", "browOuterUpRight",
            "eyeBlinkLeft", "eyeBlinkRight",
            "jawOpen", "mouthSmileLeft", "mouthSmileRight"
        ]
        
        for name in expected_names:
            assert name in result['names'], f"缺少blendshape: {name}"
        
        # 验证时间戳连续性
        frames = result['frames']
        fps = result['metadata']['fps']
        expected_interval = 1.0 / fps
        
        for i in range(1, min(10, len(frames))):
            time_diff = frames[i]['time'] - frames[i-1]['time']
            assert abs(time_diff - expected_interval) < 0.001, \
                f"时间戳不连续: {time_diff} vs {expected_interval}"
        
        # 验证权重值的合理性
        all_weights = [frame['weights'] for frame in frames]
        all_weights = np.array(all_weights)
        
        # 检查是否有变化（不应该全是0）
        assert np.any(all_weights > 0.01), "所有权重都接近0，可能有问题"
        
        # 检查嘴部动作（jawOpen应该有变化）
        jaw_open_idx = result['names'].index('jawOpen')
        jaw_open_values = all_weights[:, jaw_open_idx]
        assert np.std(jaw_open_values) > 0.01, "jawOpen没有变化"
        
        print_info("数据验证通过")
        print_info(f"权重范围: [{all_weights.min():.3f}, {all_weights.max():.3f}]")
        print_info(f"jawOpen变化范围: [{jaw_open_values.min():.3f}, {jaw_open_values.max():.3f}]")
    
    def run_all_tests(self):
        """运行所有测试"""
        print_header("LAM-A2E API 测试套件")
        
        print_info(f"服务器地址: {self.base_url}")
        print_info(f"测试音频: {self.test_audio}")
        
        # 基础测试
        print_header("基础功能测试")
        self.run_test("根路径", self.test_root_endpoint)
        self.run_test("健康检查", self.test_health_check)
        
        # 标准推理测试
        print_header("标准推理测试")
        self.run_test("标准推理（基础参数）", self.test_standard_inference_basic)
        self.run_test("标准推理（完整参数）", self.test_standard_inference_full_params)
        self.run_test("标准推理（不同ID）", self.test_standard_inference_different_ids)
        
        # 流式推理测试
        print_header("流式推理测试")
        self.run_test("流式推理初始化", self.test_streaming_init)
        self.run_test("流式推理处理chunk", self.test_streaming_chunk)
        self.run_test("流式推理多个chunk", self.test_streaming_multiple_chunks)
        self.run_test("流式推理关闭会话", self.test_streaming_close)
        
        # 错误处理测试
        print_header("错误处理测试")
        self.run_test("错误处理：无效音频", self.test_error_handling_invalid_audio)
        self.run_test("错误处理：无效会话", self.test_error_handling_invalid_session)
        
        # 高级测试
        print_header("高级测试")
        self.run_test("输出数据验证", self.test_output_validation)
        self.run_test("性能基准测试", self.test_performance_benchmark)
        
        # 打印测试结果
        self.print_summary()
    
    def print_summary(self):
        """打印测试摘要"""
        print_header("测试摘要")
        
        total = self.test_results['total']
        passed = self.test_results['passed']
        failed = self.test_results['failed']
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"总测试数: {total}")
        print_success(f"通过: {passed}")
        if failed > 0:
            print_error(f"失败: {failed}")
        else:
            print_info(f"失败: {failed}")
        
        print(f"\n通过率: {pass_rate:.1f}%")
        
        if failed == 0:
            print_success("\n🎉 所有测试通过！")
        else:
            print_warning(f"\n⚠️  有 {failed} 个测试失败")


def main():
    parser = argparse.ArgumentParser(description="LAM-A2E API 测试脚本")
    parser.add_argument("--host", type=str, default="localhost",
                       help="API服务器主机地址")
    parser.add_argument("--port", type=int, default=8000,
                       help="API服务器端口")
    parser.add_argument("--test-audio", type=str,
                       default="assets/sample_audio/BarackObama_english.wav",
                       help="测试音频文件路径")
    parser.add_argument("--test", type=str, default="all",
                       help="运行特定测试（all, basic, streaming, error, performance）")
    
    args = parser.parse_args()
    
    base_url = f"http://{args.host}:{args.port}"
    
    # 检查测试音频文件
    if not os.path.exists(args.test_audio):
        print_error(f"测试音频文件不存在: {args.test_audio}")
        print_info("请指定有效的音频文件路径，例如：")
        print_info("  python test_api.py --test-audio assets/sample_audio/BarackObama_english.wav")
        sys.exit(1)
    
    # 检查服务器连接
    try:
        response = requests.get(f"{base_url}/api/health", timeout=5)
        if response.status_code != 200:
            print_error(f"服务器响应异常: {response.status_code}")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print_error(f"无法连接到服务器: {base_url}")
        print_info("请确保API服务器正在运行：")
        print_info("  python api_server.py")
        sys.exit(1)
    except Exception as e:
        print_error(f"连接错误: {str(e)}")
        sys.exit(1)
    
    # 运行测试
    tester = APITester(base_url, args.test_audio)
    
    if args.test == "all":
        tester.run_all_tests()
    elif args.test == "basic":
        print_header("基础功能测试")
        tester.run_test("根路径", tester.test_root_endpoint)
        tester.run_test("健康检查", tester.test_health_check)
        tester.print_summary()
    elif args.test == "streaming":
        print_header("流式推理测试")
        tester.run_test("流式推理初始化", tester.test_streaming_init)
        tester.run_test("流式推理处理chunk", tester.test_streaming_chunk)
        tester.run_test("流式推理多个chunk", tester.test_streaming_multiple_chunks)
        tester.run_test("流式推理关闭会话", tester.test_streaming_close)
        tester.print_summary()
    elif args.test == "error":
        print_header("错误处理测试")
        tester.run_test("错误处理：无效音频", tester.test_error_handling_invalid_audio)
        tester.run_test("错误处理：无效会话", tester.test_error_handling_invalid_session)
        tester.print_summary()
    elif args.test == "performance":
        print_header("性能测试")
        tester.run_test("性能基准测试", tester.test_performance_benchmark)
        tester.print_summary()
    else:
        print_error(f"未知的测试类型: {args.test}")
        print_info("可用的测试类型: all, basic, streaming, error, performance")
        sys.exit(1)


if __name__ == "__main__":
    main()
