# NestJS: excepciones HTTP y validación

## Excepciones HTTP

NestJS trae excepciones que se traducen automáticamente al status code correcto.
Lanzarlas desde un service es la forma idiomática de manejar errores.

| Excepción | Status | Uso típico |
| --- | --- | --- |
| `NotFoundException` | 404 | recurso inexistente |
| `BadRequestException` | 400 | input inválido / regla de negocio |
| `UnauthorizedException` | 401 | falta autenticación |
| `ForbiddenException` | 403 | sin permisos |
| `ConflictException` | 409 | estado en conflicto (duplicado) |

```ts
import { NotFoundException } from '@nestjs/common';

getItem(id: string) {
  const item = STORE_ITEMS.find((i) => i.id === id);
  if (!item) throw new NotFoundException('Item no encontrado');
  return item;
}
```

No hay que armar la respuesta de error a mano: al lanzar `NotFoundException` el
cliente recibe `404` con un body JSON estándar.

## Validación con DTOs

Los DTOs (`Data Transfer Object`) definen la forma del input. Con
`class-validator` y `class-transformer` se validan automáticamente si hay un
`ValidationPipe` global.

```ts
import { IsString, IsInt, Min } from 'class-validator';

export class CreateItemDto {
  @IsString()
  name: string;

  @IsInt()
  @Min(0)
  price: number;
}
```

## Convención del proyecto

- Los mensajes de error van en español ("Item no encontrado", "Puntos
  insuficientes"), consistentes con el resto del backend.
- La lógica de "buscar por id o fallar" debe lanzar `NotFoundException`, no
  devolver `null` ni un objeto vacío.
