def create_trigger_handler(ability_registry):
    def handle_trigger(event, game_state, queue):
        ability_id = event.data["ability_id"]
        params = event.data.get("params", {})

        # injeta params no evento
        event.data.update(params)

        ability_registry.execute(ability_id, event, game_state, queue)

    return handle_trigger