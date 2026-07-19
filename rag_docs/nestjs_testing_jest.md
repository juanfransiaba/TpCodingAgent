# NestJS: testing unitario con Jest

El backend usa Jest. El script `npm test` (o `npm run test`) corre `jest` sobre
los archivos `*.spec.ts`. La cobertura se corre con `npm run test:cov`.

## Estructura de un test de service

Se construye un módulo de testing con `Test.createTestingModule`, mockeando las
dependencias (por ejemplo los repositorios de TypeORM).

```ts
import { Test } from '@nestjs/testing';
import { NotFoundException } from '@nestjs/common';
import { getRepositoryToken } from '@nestjs/typeorm';
import { StoreService } from './store.service';
import { UserItem } from './user-item.entity';
import { User } from '../users/entities/user.entity';

describe('StoreService', () => {
  let service: StoreService;

  beforeEach(async () => {
    const moduleRef = await Test.createTestingModule({
      providers: [
        StoreService,
        { provide: getRepositoryToken(UserItem), useValue: {} },
        { provide: getRepositoryToken(User), useValue: {} },
      ],
    }).compile();

    service = moduleRef.get(StoreService);
  });

  it('devuelve un item existente por id', () => {
    const item = service.getItem('some-known-id');
    expect(item.id).toBe('some-known-id');
  });

  it('lanza NotFoundException si el id no existe', () => {
    expect(() => service.getItem('no-existe')).toThrow(NotFoundException);
  });
});
```

## Puntos clave

- `getRepositoryToken(Entity)` es el token para mockear un repositorio inyectado
  con `@InjectRepository(Entity)`.
- Para métodos síncronos que lanzan, se testea con
  `expect(() => fn()).toThrow(...)`. Para métodos `async`, con
  `await expect(fn()).rejects.toThrow(...)`.
- Un test nuevo vive junto al código que prueba, con nombre `*.spec.ts`
  (por ejemplo `store.service.spec.ts`).

## Convención del proyecto

- Comando para correr los tests del backend: `npm test` dentro de `backend/`.
- Toda feature nueva de un service debería venir con al menos un caso feliz y un
  caso de error.
