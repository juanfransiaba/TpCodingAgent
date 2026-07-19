# NestJS: Providers, servicios y módulos

## Providers y servicios

Un provider es una clase anotada con `@Injectable()` que puede inyectarse por
constructor en otras clases. Los servicios (la lógica de negocio) son el caso
más común de provider.

```ts
import { Injectable, NotFoundException } from '@nestjs/common';

@Injectable()
export class StoreService {
  getItem(id: string) {
    const item = STORE_ITEMS.find((i) => i.id === id);
    if (!item) throw new NotFoundException('Item no encontrado');
    return item;
  }
}
```

## Inyección de dependencias

NestJS resuelve las dependencias por el tipo declarado en el constructor. No hay
que instanciar servicios a mano: el contenedor de DI las provee.

```ts
constructor(private readonly storeService: StoreService) {}
```

## Módulos

Cada feature vive en un módulo (`@Module`). El módulo declara:

- `controllers`: los controllers de la feature.
- `providers`: los servicios y otros providers que se instancian.
- `imports`: otros módulos cuyos providers exportados se necesitan.
- `exports`: providers que este módulo expone a quien lo importe.

```ts
import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';

@Module({
  imports: [TypeOrmModule.forFeature([UserItem, User])],
  controllers: [StoreController],
  providers: [StoreService],
})
export class StoreModule {}
```

## Convención del proyecto

- Un provider nuevo debe registrarse en el array `providers` de su módulo, o Nest
  lanzará un error de dependencia no resuelta al arrancar.
- Agregar un método a un service existente no requiere tocar el módulo: solo el
  service y (si expone una ruta) el controller.
