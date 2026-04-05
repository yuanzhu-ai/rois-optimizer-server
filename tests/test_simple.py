#!/usr/bin/env python3
"""
简单测试脚本
"""

import sys
sys.path.insert(0, 'D:\\temp\\git\\optimize-server')

print("测试导入...")

try:
    from src.config.config import config_manager
    print("✓ config_manager 导入成功")
    
    config = config_manager.get_config()
    print(f"✓ 配置加载成功")
    print(f"  - 服务器端口: {config.server.port}")
    print(f"  - 航司数量: {len(config.airlines)}")
    
    from src.optimizers.optimizer_manager import optimizer_manager
    print("✓ optimizer_manager 导入成功")
    
    from src.tasks.task_manager import task_manager
    print("✓ task_manager 导入成功")
    
    # 测试创建任务
    print("\n测试创建任务...")
    task_id = task_manager.create_task("BR", "PO", {"scenarioId": "3896"})
    if task_id:
        print(f"✓ 任务创建成功: {task_id}")
        
        # 测试启动任务
        print("\n测试启动任务...")
        success = task_manager.start_task(task_id)
        if success:
            print(f"✓ 任务启动成功")
        else:
            print(f"✗ 任务启动失败")
    else:
        print(f"✗ 任务创建失败")
    
except Exception as e:
    print(f"✗ 错误: {e}")
    import traceback
    traceback.print_exc()
