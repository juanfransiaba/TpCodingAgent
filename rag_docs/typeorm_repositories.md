# TypeORM en NestJS: entidades y repositorios

## Entidades

Una entidad es una clase decorada con `@Entity()` que mapea a una tabla. Sus
columnas se declaran con `@Column`, `@PrimaryGeneratedColumn`, etc.

```ts
import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn } from 'typeorm';

@Entity()
export class UserItem {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  userId: string;

  @Column()
  itemId: string;

  @CreateDateColumn()
  purchasedAt: Date;
}
```

## Repositorios

El patrón repository de TypeORM da acceso a la persistencia de una entidad. En
NestJS se inyecta con `@InjectRepository(Entity)`:

```ts
constructor(
  @InjectRepository(UserItem) private readonly userItemRepo: Repository<UserItem>,
) {}
```

Métodos habituales:

- `repo.find({ where, order })`: lista filas que cumplen la condición.
- `repo.findOne({ where })`: una fila o `null`.
- `repo.create(partial)`: crea una instancia en memoria (no persiste).
- `repo.save(entity)`: inserta o actualiza en la base.

## Registro del repositorio

Para inyectar un repositorio, su entidad debe estar en
`TypeOrmModule.forFeature([...])` dentro del módulo:

```ts
@Module({
  imports: [TypeOrmModule.forFeature([UserItem, User])],
})
export class StoreModule {}
```

## Convención del proyecto

- Los datos estáticos (catálogo de ítems de la tienda) viven en un archivo
  `*.const.ts` como arreglo en memoria, no en la base; solo la propiedad del
  usuario sobre esos ítems se persiste vía repositorio.
- Buscar un ítem del catálogo por id es un `Array.find` sobre esa constante, no
  una consulta al repositorio.
