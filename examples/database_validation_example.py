#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库验证和修复工具使用示例
"""

import os
import sys
import logging
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database_manager import DatabaseManager
from core.database_validator import DatabaseValidator, ValidationLevel

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """主函数"""
    
    # 数据库文件路径（实际使用时应该是真实的数据库路径）
    db_path = "example_database.db"
    
    try:
        # 创建数据库管理器
        db_manager = DatabaseManager(db_path)
        
        # 连接数据库
        if not db_manager.connect():
            logger.error("无法连接到数据库")
            return
        
        # 初始化数据库（如果需要）
        logger.info("初始化数据库")
        if not db_manager.initialize_database():
            logger.error("数据库初始化失败")
            return
        
        # 创建验证器
        validator = DatabaseValidator(db_manager)
        
        print("=== 数据库验证和修复工具示例 ===\n")
        
        # 1. 执行基本验证
        print("1. 执行基本验证...")
        basic_result = validator.validate_database(ValidationLevel.BASIC)
        print(f"   结果: {'✓ 通过' if basic_result.success else '✗ 发现问题'}")
        print(f"   检查项: {basic_result.total_checks}, 通过: {basic_result.passed_checks}")
        print(f"   发现问题: {len(basic_result.issues)} 个")
        
        if basic_result.issues:
            print("   问题详情:")
            for issue in basic_result.issues[:3]:  # 只显示前3个问题
                print(f"     - {issue.severity.value.upper()}: {issue.description}")
            if len(basic_result.issues) > 3:
                print(f"     ... 还有 {len(basic_result.issues) - 3} 个问题")
        print()
        
        # 2. 执行标准验证
        print("2. 执行标准验证...")
        standard_result = validator.validate_database(ValidationLevel.STANDARD)
        print(f"   结果: {'✓ 通过' if standard_result.success else '✗ 发现问题'}")
        print(f"   检查项: {standard_result.total_checks}, 通过: {standard_result.passed_checks}")
        print(f"   发现问题: {len(standard_result.issues)} 个")
        print(f"   耗时: {standard_result.duration:.3f} 秒")
        print()
        
        # 3. 自动修复（如果有可修复的问题）
        auto_fixable_issues = [issue for issue in standard_result.issues if issue.auto_fixable]
        if auto_fixable_issues:
            print(f"3. 自动修复 {len(auto_fixable_issues)} 个可修复问题...")
            fix_result = validator.auto_fix_issues(auto_fixable_issues)
            print(f"   结果: {'✓ 成功' if fix_result['success'] else '✗ 部分失败'}")
            print(f"   修复成功: {fix_result['fixed_count']} 个")
            print(f"   修复失败: {fix_result['failed_count']} 个")
            
            if fix_result['errors']:
                print("   错误信息:")
                for error in fix_result['errors'][:2]:
                    print(f"     - {error}")
            print()
        else:
            print("3. 没有可自动修复的问题")
            print()
        
        # 4. 数据库优化
        print("4. 执行数据库优化...")
        optimize_result = validator.optimize_database()
        print(f"   结果: {'✓ 成功' if optimize_result['success'] else '✗ 部分失败'}")
        print(f"   执行操作: {len(optimize_result['operations'])} 个")
        
        if optimize_result['operations']:
            print("   操作详情:")
            for operation in optimize_result['operations'][:3]:
                print(f"     ✓ {operation}")
            if len(optimize_result['operations']) > 3:
                print(f"     ... 还有 {len(optimize_result['operations']) - 3} 个操作")
        
        if optimize_result['errors']:
            print("   错误信息:")
            for error in optimize_result['errors'][:2]:
                print(f"     ✗ {error}")
        print()
        
        # 5. 生成健康报告
        print("5. 生成数据库健康报告...")
        health_report = validator.get_database_health_report()
        
        # 数据库基本信息
        db_info = health_report['database_info']
        print(f"   数据库文件: {os.path.basename(db_info.get('file_path', 'N/A'))}")
        print(f"   文件大小: {db_info.get('file_size_mb', 0):.2f} MB")
        print(f"   数据库版本: {db_info.get('version', 'N/A')}")
        print(f"   表数量: {db_info.get('table_count', 0)}")
        print(f"   总记录数: {db_info.get('record_count', 0)}")
        
        # 表统计信息
        print("\n   表统计信息:")
        for table, stats in health_report['table_statistics'].items():
            record_count = stats.get('record_count', 0)
            print(f"     {table}: {record_count} 条记录")
            
            # 如果是projects表，显示更多信息
            if table == 'projects' and 'active_projects' in stats:
                active = stats.get('active_projects', 0)
                inactive = stats.get('inactive_projects', 0)
                avg_api = stats.get('avg_api_count', 0)
                print(f"       活跃项目: {active}, 非活跃: {inactive}")
                print(f"       平均API数: {avg_api:.1f}")
        
        # 性能指标
        perf_metrics = health_report['performance_metrics']
        if perf_metrics:
            print(f"\n   性能指标:")
            print(f"     索引数量: {perf_metrics.get('index_count', 0)}")
            print(f"     缓存条目: {perf_metrics.get('cache_entries', 0)}")
        
        # 优化建议
        recommendations = health_report['recommendations']
        if recommendations:
            print(f"\n   优化建议:")
            for rec in recommendations:
                print(f"     • {rec}")
        else:
            print(f"\n   ✓ 数据库状态良好，暂无优化建议")
        
        print(f"\n=== 示例完成 ===")
        
        # 清理示例数据库文件
        if os.path.exists(db_path):
            try:
                db_manager.disconnect()
                os.remove(db_path)
                print(f"已清理示例数据库文件: {db_path}")
            except Exception as e:
                print(f"清理文件失败: {e}")
        
    except Exception as e:
        logger.error(f"示例执行失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())