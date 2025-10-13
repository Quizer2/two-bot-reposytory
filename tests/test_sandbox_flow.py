def test_sandbox_flow():
    # EventBus -> OrderSubmitted -> audit log, then adapter builds normalized order
    from utils.event_bus import publish_event
    try:
        from utils.events_schema import OrderSubmitted
        publish_event(OrderSubmitted(bot_id='TBOT', symbol='BTCUSDT', side='buy', qty=0.01, price=None))
    except Exception:
        publish_event('OrderSubmitted', {'bot_id':'TBOT','symbol':'BTCUSDT','side':'buy','qty':0.01})
    from utils.adapters.exchange_adapter import ExchangeAdapter
    from utils.orders import build_order
    ad = ExchangeAdapter()
    ad.set_rules('BTCUSDT', 0.0001, 0.0001, 0.1)
    order = build_order(ad, 'TBOT', 'BTCUSDT', 'buy', 0.00555, 61234.59)
    assert 'clientOrderId' in order and order['qty'] <= 0.00555 and order['price'] <= 61234.59
