import { useState, useEffect } from 'react';
import { Modal, Form, Input, Select, Button, Space, Typography } from 'antd';
import { PlusOutlined } from '@ant-design/icons';

const { TextArea } = Input;
const { Option } = Select;
const { Text } = Typography;

const DEFAULT_TAGS = ['重要', '待阅读', '已阅读', 'AI', '科技', '财经', '生活'];

const FavoriteModal = ({ visible, item, onCancel, onConfirm }) => {
  const [form] = Form.useForm();

  useEffect(() => {
    if (visible) {
      form.resetFields();
    }
  }, [visible, form]);

  const handleOk = () => {
    form.validateFields().then(values => {
      onConfirm(values.tags || [], values.remark || '');
    });
  };

  return (
    <Modal
      title="收藏内容"
      open={visible}
      onOk={handleOk}
      onCancel={onCancel}
      okText="确认收藏"
      cancelText="取消"
      destroyOnHidden
    >
      <Form form={form} layout="vertical">
        <div style={{ marginBottom: 16 }}>
          <Text strong>标题：</Text>
          <Text>{item?.title || item?.title_snapshot || '无标题'}</Text>
        </div>

        <Form.Item
          label="标签"
          name="tags"
        >
          <Select
            mode="tags"
            style={{ width: '100%' }}
            placeholder="添加标签（可自定义）"
            options={DEFAULT_TAGS.map(tag => ({ value: tag, label: tag }))}
            tokenSeparators={[',']}
          />
        </Form.Item>

        <Form.Item
          label="备注"
          name="remark"
        >
          <TextArea
            rows={4}
            placeholder="添加备注说明（可选）"
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default FavoriteModal;
