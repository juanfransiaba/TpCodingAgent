# NestJS: Controllers y routing

Los controllers manejan las requests HTTP entrantes y devuelven respuestas al
cliente. Se declaran con el decorador `@Controller(prefix)`, donde `prefix` es el
segmento base de la ruta.

```ts
import { Controller, Get, Post, Param, Body, UseGuards } from '@nestjs/common';

@Controller('store')
export class StoreController {
  constructor(private readonly storeService: StoreService) {}

  @Get('items')
  getItems() {
    return this.storeService.getItems();
  }

  @Get('items/:id')
  getItem(@Param('id') id: string) {
    return this.storeService.getItem(id);
  }

  @Post('buy/:itemId')
  buy(@Param('itemId') itemId: string) {
    return this.storeService.buy(itemId);
  }
}
```

## Decoradores de método

- `@Get()`, `@Post()`, `@Put()`, `@Patch()`, `@Delete()` mapean el método HTTP.
- El argumento del decorador es el sub-path relativo al prefijo del controller.
  `@Get('items/:id')` dentro de `@Controller('store')` responde a `GET /store/items/:id`.

## Route params y query

- `@Param('id') id: string` extrae un parámetro de ruta (`:id`).
- `@Query('q') q: string` extrae un query param (`?q=...`).
- `@Body() dto: CreateItemDto` extrae el cuerpo del request.

Los route params siempre llegan como `string`; si se necesita un número hay que
parsearlo (por ejemplo con `ParseIntPipe`).

## Convención del proyecto

- Un controller delega la lógica al service inyectado; no contiene lógica de
  negocio ni acceso directo a la base de datos.
- Las rutas de lectura de un recurso por id siguen el patrón `@Get(':id')` y el
  service es responsable de lanzar `NotFoundException` si el recurso no existe.
- El controller se registra en el array `controllers` de su módulo.
