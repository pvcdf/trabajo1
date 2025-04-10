from fastapi import FastAPI, HTTPException, Depends, Query
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session
from datetime import datetime
from pydantic import BaseModel

DATABASE_URL = "sqlite:///./database.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Mision(Base):
    __tablename__ = 'misiones'
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)
    descripcion = Column(Text, nullable=True)
    experiencia = Column(Integer, default=0)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    personajes = relationship("MisionPersonaje", back_populates="mision")

class Personaje(Base):
    __tablename__ = 'personajes'
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(30), nullable=False)
    experiencia = Column(Integer, default=0)

    misiones = relationship("MisionPersonaje", back_populates="personaje")

class MisionPersonaje(Base):
    __tablename__ = 'misiones_personaje'
    id = Column(Integer, primary_key=True, index=True)

    personaje_id = Column(Integer, ForeignKey('personajes.id'))
    mision_id = Column(Integer, ForeignKey('misiones.id'))
    orden = Column(Integer)
    estado = Column(Boolean, default=False)

    personaje = relationship("Personaje", back_populates="misiones")
    mision = relationship("Mision", back_populates="personajes")


Base.metadata.create_all(bind=engine)

app = FastAPI()

class MisionCreate(BaseModel):
    nombre: str
    descripcion: str
    experiencia: int

class MisionResponse(BaseModel):
    id: int
    nombre: str
    descripcion: str
    experiencia: int
    fecha_creacion: datetime
    class Config:
        orm_mode = True

class PersonajeCreate(BaseModel):
    nombre: str

class PersonajeResponse(PersonajeCreate):
    id: int
    experiencia: int
    class Config:
        orm_mode = True

class CompletarMisionRequest(BaseModel):
    personaje_id: int
    mision_id: int

class AceptarMisionRequest(BaseModel):
    personaje_id: int
    mision_id: int
    orden: int = 0

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/misiones", response_model=list[MisionResponse])
def obtener_misiones_por_personaje(personaje_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        personaje = db.query(Personaje).filter(Personaje.id == personaje_id).first()
        if not personaje:
            raise HTTPException(status_code=404, detail="Personaje no encontrado")

        relaciones = db.query(MisionPersonaje).join(Mision).filter(
            MisionPersonaje.personaje_id == personaje_id,
            MisionPersonaje.estado == False
        ).order_by(MisionPersonaje.orden.asc()).all()

        misiones = [relacion.mision for relacion in relaciones]
        return misiones

    except Exception as e:
        print("Error al obtener misiones:", str(e))
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/misiones/{id}", response_model=MisionResponse)
def obtener_mision(id: int, db: Session = Depends(get_db)):
    mision = db.query(Mision).filter(Mision.id == id).first()
    if not mision:
        raise HTTPException(status_code=404, detail="Misión no encontrada")
    return mision

@app.post("/misiones", response_model=MisionResponse)
def crear_mision(mision: MisionCreate, db: Session = Depends(get_db)):
    nueva_mision = Mision(**mision.dict())
    db.add(nueva_mision)
    db.commit()
    db.refresh(nueva_mision)
    return nueva_mision

@app.put("/misiones/{id}", response_model=MisionResponse)
def actualizar_mision(id: int, descripcion: str, db: Session = Depends(get_db)):
    mision = db.query(Mision).filter(Mision.id == id).first()
    if not mision:
        raise HTTPException(status_code=404, detail="Misión no encontrada")
    mision.descripcion = descripcion
    db.commit()
    db.refresh(mision)
    return mision

@app.delete("/misiones/{id}")
def eliminar_mision(id: int, db: Session = Depends(get_db)):
    mision = db.query(Mision).filter(Mision.id == id).first()
    if not mision:
        raise HTTPException(status_code=404, detail="Misión no encontrada")
    db.delete(mision)
    db.commit()
    return {"mensaje": "Misión eliminada"}

@app.get("/personajes", response_model=list[PersonajeResponse])
def obtener_personajes(db: Session = Depends(get_db)):
    return db.query(Personaje).all()

@app.post("/personajes", response_model=PersonajeResponse)
def crear_personaje(personaje: PersonajeCreate, db: Session = Depends(get_db)):
    nuevo_personaje = Personaje(**personaje.dict())
    db.add(nuevo_personaje)
    db.commit()
    db.refresh(nuevo_personaje)
    return nuevo_personaje

@app.post("/aceptar_mision")
def aceptar_mision(request: AceptarMisionRequest, db: Session = Depends(get_db)):
    personaje = db.query(Personaje).filter(Personaje.id == request.personaje_id).first()
    mision = db.query(Mision).filter(Mision.id == request.mision_id).first()

    if not personaje:
        raise HTTPException(status_code=404, detail="Personaje no encontrado")
    if not mision:
        raise HTTPException(status_code=404, detail="Misión no encontrada")

    ya_asignada = db.query(MisionPersonaje).filter_by(
        personaje_id=request.personaje_id,
        mision_id=request.mision_id,
        estado=False 
    ).first()

    if ya_asignada:
        raise HTTPException(status_code=400, detail="La misión ya fue aceptada por este personaje")



    nueva_relacion = MisionPersonaje(
        personaje_id=request.personaje_id,
        mision_id=request.mision_id,
        orden=request.orden
    )
    db.add(nueva_relacion)
    db.commit()

    return {"mensaje": "Misión aceptada correctamente"}

@app.post("/completar_mision")
def completar_mision(request: CompletarMisionRequest, db: Session = Depends(get_db)):
    mision = db.query(Mision).filter(Mision.id == request.mision_id).first()
    personaje = db.query(Personaje).filter(Personaje.id == request.personaje_id).first()
    relacion = db.query(MisionPersonaje).filter_by(
        personaje_id=request.personaje_id,
        mision_id=request.mision_id,
        estado=False
    ).order_by(MisionPersonaje.orden.asc()).first()

    if not mision:
        raise HTTPException(status_code=404, detail="Misión no encontrada")
    if not personaje:
        raise HTTPException(status_code=404, detail="Personaje no encontrado")
    if not relacion:
        raise HTTPException(status_code=400, detail="El personaje no tiene asignada esta misión")
    if relacion.estado:
        raise HTTPException(status_code=400, detail="La misión ya fue completada para este personaje")

    personaje.experiencia += mision.experiencia
    relacion.estado = True

    db.commit()
    return {
        "mensaje": "Misión completada con éxito",
        "experiencia_ganada": mision.experiencia,
        "experiencia_total": personaje.experiencia
    }


class ColaMisiones:
    def __init__(self, db: Session, personaje_id: int):
        self.db = db
        self.personaje_id = personaje_id

    def enqueue(self, mision_id: int):
        max_orden = self.db.query(MisionPersonaje).filter_by(
            personaje_id=self.personaje_id
        ).order_by(MisionPersonaje.orden.desc()).first()
        siguiente_orden = max_orden.orden + 1 if max_orden else 0

        nueva_relacion = MisionPersonaje(
            personaje_id=self.personaje_id,
            mision_id=mision_id,
            orden=siguiente_orden
        )
        self.db.add(nueva_relacion)
        self.db.commit()
        return {"mensaje": "Misión encolada correctamente"}

    def dequeue(self):
        primera = self.db.query(MisionPersonaje).filter_by(
            personaje_id=self.personaje_id,
            estado=False
        ).order_by(MisionPersonaje.orden.asc()).first()

        if not primera:
            raise HTTPException(status_code=404, detail="La cola está vacía")

        self.db.delete(primera)
        self.db.commit()
        return {"mensaje": "Misión eliminada de la cola", "mision_id": primera.mision_id}

    def first(self):
        primera = self.db.query(MisionPersonaje).filter_by(
            personaje_id=self.personaje_id,
            estado=False
        ).order_by(MisionPersonaje.orden.asc()).first()

        if not primera:
            raise HTTPException(status_code=404, detail="La cola está vacía")
        return primera.mision

    def is_empty(self):
        cantidad = self.db.query(MisionPersonaje).filter_by(
            personaje_id=self.personaje_id,
            estado=False
        ).count()
        return {"cola_vacia": cantidad == 0}

    def size(self):
        cantidad = self.db.query(MisionPersonaje).filter_by(
            personaje_id=self.personaje_id,
            estado=False
        ).count()
        return {"cantidad": cantidad}


@app.post("/cola/{personaje_id}/enqueue")
def encolar_mision(personaje_id: int, mision_id: int, db: Session = Depends(get_db)):
    cola = ColaMisiones(db, personaje_id)
    return cola.enqueue(mision_id)

@app.post("/cola/{personaje_id}/dequeue")
def desencolar_mision(personaje_id: int, db: Session = Depends(get_db)):
    cola = ColaMisiones(db, personaje_id)
    return cola.dequeue()

@app.get("/cola/{personaje_id}/first", response_model=MisionResponse)
def ver_primera_mision(personaje_id: int, db: Session = Depends(get_db)):
    cola = ColaMisiones(db, personaje_id)
    return cola.first()

@app.get("/cola/{personaje_id}/is_empty")
def cola_vacia(personaje_id: int, db: Session = Depends(get_db)):
    cola = ColaMisiones(db, personaje_id)
    return cola.is_empty()

@app.get("/cola/{personaje_id}/size")
def tamaño_cola(personaje_id: int, db: Session = Depends(get_db)):
    cola = ColaMisiones(db, personaje_id)
    return cola.size()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
