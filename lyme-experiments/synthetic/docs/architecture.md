# Architecture

## Module Overview

- **auth.py**: Core auth module
- **config.py**: Core config module
- **database.py**: Core database module
- **engine.py**: Core engine module
- **factory.py**: Core factory module
- **handler.py**: Core handler module
- **injector.py**: Core injector module
- **loader.py**: Core loader module
- **manager.py**: Core manager module
- **parser.py**: Core parser module
- **provider.py**: Core provider module
- **registry.py**: Core registry module
- **service.py**: Core service module
- **store.py**: Core store module
- **utils.py**: Core utils module
- **validator.py**: Core validator module
- **worker.py**: Core worker module
- **adapter.py**: Core adapter module
- **builder.py**: Core builder module
- **controller.py**: Core controller module

## Dependencies

- auth.py depends on: factory, config, parser
- config.py depends on: auth, engine, loader
- database.py depends on: controller, parser, auth
- engine.py depends on: registry, factory, database
- factory.py depends on: validator, builder, engine
- handler.py depends on: manager, provider, database
- injector.py depends on: service, controller, loader
- loader.py depends on: store, parser, manager
- manager.py depends on: database, injector, registry
- parser.py depends on: factory, loader, manager
- provider.py depends on: worker, database, config
- registry.py depends on: validator, adapter, manager
- service.py depends on: utils, handler, validator
- store.py depends on: adapter, injector, factory
- utils.py depends on: registry, parser, loader
- validator.py depends on: factory, controller, worker
- worker.py depends on: parser, service, registry
- adapter.py depends on: provider, auth, loader
- builder.py depends on: config, provider, database
- controller.py depends on: builder, validator, loader

## API Surface

- auth.py exports: create_auth, validate_auth
- config.py exports: create_config, verify_config
- database.py exports: get_database, verify_database
- engine.py exports: validate_engine, validate_engine
- factory.py exports: validate_factory, validate_factory
- handler.py exports: create_handler, validate_handler
- injector.py exports: update_injector, verify_injector
- loader.py exports: delete_loader, validate_loader
- manager.py exports: create_manager, verify_manager
- parser.py exports: save_parser, check_parser
- provider.py exports: handle_provider, validate_provider
- registry.py exports: load_registry, validate_registry
- service.py exports: process_service, verify_service
- store.py exports: delete_store, validate_store
- utils.py exports: process_utils, validate_utils
- validator.py exports: load_validator, validate_validator
- worker.py exports: transform_worker, verify_worker
- adapter.py exports: save_adapter, validate_adapter
- builder.py exports: load_builder, validate_builder
- controller.py exports: transform_controller, check_controller