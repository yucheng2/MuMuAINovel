import React, { useState } from 'react';
import { Modal, Input, Space, Typography, message, Button } from 'antd';
import { BulbOutlined } from '@ant-design/icons';
import { inspirationAutoApi } from '../services/api';
import { eventBus } from '../store/eventBus';

const { TextArea } = Input;
const { Text } = Typography;

interface InspirationAutoModalProps {
  open: boolean;
  onClose: () => void;
}

export const InspirationAutoModal: React.FC<InspirationAutoModalProps> = ({
  open,
  onClose,
}) => {
  const [idea, setIdea] = useState('');
  const [loading, setLoading] = useState(false);

  const handleCreate = async () => {
    if (!idea.trim()) {
      message.warning('请输入创作想法');
      return;
    }

    setLoading(true);
    try {
      await inspirationAutoApi.createAutoTask(idea.trim());
      message.success('灵感后台任务已创建');
      eventBus.emit('background-task-created');
      setIdea('');
      onClose();
    } catch (error: any) {
      console.error('创建灵感后台任务失败:', error);
      message.error(error?.response?.data?.detail || '创建失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    if (!loading) {
      setIdea('');
      onClose();
    }
  };

  return (
    <Modal
      title={
        <Space>
          <BulbOutlined style={{ color: '#faad14' }} />
          <span>灵感后台创建</span>
        </Space>
      }
      open={open}
      onCancel={handleCancel}
      closable={!loading}
      maskClosable={!loading}
      keyboard={!loading}
      footer={
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            将自动生成书名、简介、主题等全部内容
          </Text>
          <Space>
            <Button onClick={handleCancel} disabled={loading}>
              取消
            </Button>
            <Button type="primary" onClick={handleCreate} loading={loading}>
              开始创建
            </Button>
          </Space>
        </Space>
      }
      width={500}
      centered
    >
      <div style={{ marginBottom: 16 }}>
        <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
          输入你的创作想法：
        </Text>
        <TextArea
          value={idea}
          onChange={(e) => setIdea(e.target.value)}
          placeholder="例如：写一个穿越到古代成为王妃的故事"
          rows={4}
          maxLength={500}
          showCount
          disabled={loading}
        />
      </div>
    </Modal>
  );
};

export default InspirationAutoModal;
