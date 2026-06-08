import { Badge, Breadcrumb, Space, Typography } from 'antd';

const { Title, Text } = Typography;

export default function PageHeader({ title, description, breadcrumb, extra, tags }) {
  return (
    <header className="page-header">
      {breadcrumb?.length > 0 && (
        <Breadcrumb items={breadcrumb} style={{ marginBottom: 8 }} />
      )}
      <div className="page-header-row">
        <div className="page-header-main">
          <Space align="center" wrap>
            <Title level={2} style={{ margin: 0 }}>
              {title}
            </Title>
            {tags}
          </Space>
          {description && (
            <Text type="secondary" className="page-header-desc">
              {description}
            </Text>
          )}
        </div>
        {extra && <div className="page-header-extra">{extra}</div>}
      </div>
    </header>
  );
}

export function StatusBadge({ status, text }) {
  const color = status === 'ok' ? 'success' : status === 'warn' ? 'warning' : 'default';
  return <Badge status={color} text={text} />;
}
