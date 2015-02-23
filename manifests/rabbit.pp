class { '::rabbitmq':
  service_manage    => false,
  port              => '5672',
}
