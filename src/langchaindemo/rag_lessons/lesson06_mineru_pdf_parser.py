"""
Lesson 06: 使用 MinerU API 解析 PDF 文档

流程：
1. 调用 MinerU 批量上传接口，获取临时上传链接
2. 上传本地 PDF 文件
3. 轮询解析结果，获取最终下载地址（zip 包）

注意：需要配置环境变量 MINERU_TOKEN
"""

import os
import time
import requests
from pathlib import Path

from langchaindemo.config import ROOT_DIR
from langchaindemo.config import (
    MINERU_TOKEN,
)


def mineru_upload_file(file_paths, data_ids, model_version="vlm"):
    """上传文件并返回 batch_id"""
    token = MINERU_TOKEN
    if not token:
        raise ValueError("请设置 MINERU_TOKEN 环境变量")

    url = "https://mineru.net/api/v4/file-urls/batch"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    # 构建 files 列表
    files = []
    for path, data_id in zip(file_paths, data_ids):
        files.append({"name": Path(path).name, "data_id": data_id})

    data = {
        "files": files,
        "model_version": model_version
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()

        if result.get("code") != 0:
            print(f"申请上传链接失败: {result.get('msg')}")
            return None

        batch_id = result["data"]["batch_id"]
        upload_urls = result["data"]["file_urls"]
        print(f"batch_id: {batch_id}, 需要上传 {len(upload_urls)} 个文件")

        for i, upload_url in enumerate(upload_urls):
            with open(file_paths[i], 'rb') as f:
                res_upload = requests.put(upload_url, data=f, timeout=60)
                if res_upload.status_code == 200:
                    print(f"文件 {Path(file_paths[i]).name} 上传成功")
                else:
                    print(f"文件 {Path(file_paths[i]).name} 上传失败: {res_upload.status_code}")

        return batch_id

    except requests.RequestException as e:
        print(f"上传请求异常: {e}")
        return None


def mineru_check_result(batch_id, max_wait=1800, interval=8):
    """轮询查询批量解析结果"""
    if not batch_id:
        print("batch_id 为空，无法查询")
        return None

    token = MINERU_TOKEN
    url = f"https://mineru.net/api/v4/extract-results/batch/{batch_id}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    start_time = time.time()
    last_state = None

    while True:
        if time.time() - start_time > max_wait:
            print(f"\n超时（{max_wait}秒），终止轮询")
            return None

        try:
            res = requests.get(url, headers=headers, timeout=30)
            res.raise_for_status()
            result = res.json()

            if result.get("code") != 0:
                print(f"查询失败: {result.get('msg')}")
                return None

            extract_results = result.get("data", {}).get("extract_result", [])
            if not extract_results:
                print("extract_result 为空，等待中...")
                time.sleep(interval)
                continue

            state = extract_results[0].get("state", "unknown")

            if state != last_state:
                print(f"\n状态变更: {state}")
                last_state = state

            if state == "done":
                full_zip_url = extract_results[0].get("full_zip_url")
                print(f"提取完成！下载地址: {full_zip_url}")
                return full_zip_url
            elif state == "failed":
                print(f"解析失败: {extract_results[0].get('err_msg', '未知错误')}")
                return None

            print(f"当前状态: {state}，等待 {interval} 秒后重试...", end="\r")
            time.sleep(interval)

        except requests.RequestException as e:
            print(f"查询请求异常: {e}")
            time.sleep(interval)

if __name__ == '__main__':
    # 1. 准备待上传的 PDF 文件列表（可多个，逐个添加）
    pdf_paths = [
        str(ROOT_DIR / "data" / "sample.pdf"),
    ]
    # 2. 为每个文件准备一个唯一的 data_id（用于区分同一批次的不同文件）
    data_ids = [
        "sample_pdf_001",
    ]

    # 3. 校验文件是否存在
    for path in pdf_paths:
        if not Path(path).exists():
            print(f"❌ 文件不存在: {path}")
            exit(1)

    # 4. 上传文件，拿到 batch_id
    batch_id = mineru_upload_file(pdf_paths, data_ids)
    if not batch_id:
        print("❌ 上传失败，终止流程")
        exit(1)

    # 5. 轮询解析结果
    zip_url = mineru_check_result(batch_id)
    if zip_url:
        print(f"\n✅ 最终下载地址: {zip_url}")
        print("提示: 你可以手动下载这个 zip，里面包含 Markdown、图片、JSON 等解析结果。")
    else:
        print("\n❌ 解析失败或超时")